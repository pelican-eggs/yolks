"""Create a patched copy of an exact Windrose 0.10.0 native backup ZIP."""

import argparse
import copy
import hashlib
import json
import re
import shutil
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

WORLD_MEMBER = "AdditionalRecordFiles/WorldDescription.json"
MAX_DESCRIPTOR = 1024 * 1024
MAX_BACKUP_BYTES = 2 * 1024**3
PRESETS = {
    "Easy": (0.7, 0.6, 0.7, 0.6, 0.7, "Easy"),
    "Medium": (1.0, 1.0, 1.0, 1.0, 1.0, "Normal"),
    "Hard": (1.5, 1.25, 1.5, 1.25, 1.5, "Hard"),
}


def reject_duplicate_keys(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("The world descriptor contains duplicate keys.")
    return result


def tag(name):
    return json.dumps({"TagName": f"WDS.Parameter.{name}"})


def edit_descriptor(data, expected_id, name, preset):
    original = json.loads(data, object_pairs_hook=reject_duplicate_keys)
    world = original["WorldDescription"]
    if world["islandId"] != expected_id or type(world["CreationTime"]) not in (float, int):
        raise ValueError("The backup descriptor does not identify the expected world.")
    if preset not in PRESETS or not 1 <= len(name.strip()) <= 64 or any(ord(c) < 32 for c in name):
        raise ValueError("Invalid world name or difficulty.")
    health, damage, ship_health, ship_damage, boarding, combat = PRESETS[preset]
    settings = {
        "BoolParameters": {tag("Coop.SharedQuests"): True, tag("EasyExplore"): False},
        "FloatParameters": {
            tag("MobHealthMultiplier"): health,
            tag("MobDamageMultiplier"): damage,
            tag("ShipsHealthMultiplier"): ship_health,
            tag("ShipsDamageMultiplier"): ship_damage,
            tag("BoardingDifficultyMultiplier"): boarding,
            tag("Coop.StatsCorrectionModifier"): 1.0,
            tag("Coop.ShipStatsCorrectionModifier"): 0.0,
        },
        "TagParameters": {
            tag("CombatDifficulty"): {"TagName": f"WDS.Parameter.CombatDifficulty.{combat}"},
        },
    }
    world.update(WorldName=name, WorldPresetType=preset, WorldSettings=settings)
    return (json.dumps(original, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode()


def validated_members(archive):
    members = archive.infolist()
    names = [item.filename for item in members]
    if len(names) != len(set(names)) or names.count(WORLD_MEMBER) != 1:
        raise ValueError("The backup lacks exactly one world descriptor or contains duplicate members.")
    if archive.getinfo(WORLD_MEMBER).file_size > MAX_DESCRIPTOR:
        raise ValueError("The world descriptor exceeds its size limit.")
    if sum(item.file_size for item in members) > MAX_BACKUP_BYTES:
        raise ValueError("The fresh world backup exceeds the total size limit.")
    for item in members:
        path = PurePosixPath(item.filename)
        kind = (item.external_attr >> 16) & 0o170000
        if path.is_absolute() or ".." in path.parts or "\\" in item.filename or ":" in item.filename:
            raise ValueError("The backup contains an invalid member path.")
        if kind not in (0, 0o040000, 0o100000) or item.flag_bits & 1:
            raise ValueError("The backup contains a link, special file or encrypted member.")
    return members


def patch_backup(source, target, world_id, world_name, preset):
    if not re.fullmatch("[A-Fa-f0-9]{32}", world_id):
        raise ValueError("Invalid world ID.")
    if source.name != f"{world_id}_0.10.0_Latest.zip" or not source.is_file() or source.is_symlink():
        raise ValueError("This helper requires the selected 0.10.0 latest world backup.")
    if source.resolve() == target.resolve():
        raise ValueError("The original backup must be preserved.")
    with ZipFile(source) as previous:
        members = validated_members(previous)
        descriptor = edit_descriptor(previous.read(WORLD_MEMBER), world_id, world_name, preset)
        with target.open("xb") as stream:
            try:
                with ZipFile(stream, "w", allowZip64=True) as updated:
                    updated.comment = previous.comment
                    for member in members:
                        metadata = copy.copy(member)
                        if member.filename == WORLD_MEMBER:
                            updated.writestr(metadata, descriptor)
                        else:
                            with previous.open(member) as reader, updated.open(metadata, "w") as writer:
                                shutil.copyfileobj(reader, writer, length=256 * 1024)
                with ZipFile(target) as result:
                    actual = validated_members(result)
                    if result.testzip() is not None or result.read(WORLD_MEMBER) != descriptor:
                        raise ValueError("The patched backup did not pass CRC and descriptor verification.")
                    if [m.filename for m in actual] != [m.filename for m in members]:
                        raise ValueError("The patched backup inventory changed.")
                    for before, after in zip(members, actual, strict=True):
                        if before.filename == WORLD_MEMBER:
                            continue
                        with previous.open(before) as left, result.open(after) as right:
                            if hashlib.file_digest(left, "sha256").digest() != hashlib.file_digest(right, "sha256").digest():
                                raise ValueError("A non-descriptor member changed.")
            except BaseException:
                stream.close()
                target.unlink(missing_ok=True)
                raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("world_id")
    parser.add_argument("world_name")
    parser.add_argument("preset", choices=PRESETS)
    args = parser.parse_args()
    patch_backup(args.source, args.target, args.world_id, args.world_name, args.preset)
