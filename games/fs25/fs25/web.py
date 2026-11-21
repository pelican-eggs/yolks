"""GIANTS dedicated-server web forms, with a session bound to one local origin."""

from dataclasses import dataclass, field
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from urllib.error import URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener
import ssl


@dataclass
class Form:
    fields: list = field(default_factory=list)
    controls: set = field(default_factory=set)

    def payload(self, **updates):
        return urlencode([(key, value) for key, value in self.fields if key not in updates] +
                         [(key, value) for key, value in updates.items() if value is not None]).encode()


class Forms(HTMLParser):
    def __init__(self, page):
        super().__init__(convert_charrefs=True)
        self.forms = []
        self.form = None
        self.select = None
        self.option = None
        self.feed(page)
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.form = Form()
            self.forms.append(self.form)
            self.select = self.option = None
        if self.form is None or "disabled" in attrs:
            return
        name = attrs.get("name")
        if name:
            self.form.controls.add(name)
        if tag == "input" and name:
            kind = (attrs.get("type") or "text").lower()
            if kind in {"submit", "image", "button", "reset", "file"}:
                return
            if kind in {"checkbox", "radio"} and "checked" not in attrs:
                return
            default = "on" if kind in {"checkbox", "radio"} else ""
            self.form.fields.append((name, attrs.get("value", default) or ""))
        elif tag == "select" and name:
            self.select = (name, "multiple" in attrs, [])
        elif tag == "option" and self.select:
            self.finish_option()
            self.option = [attrs.get("value"), "", "selected" in attrs, "disabled" in attrs]

    def handle_data(self, data):
        if self.option is not None:
            self.option[1] += data

    def finish_option(self):
        if self.option is not None:
            value, label, selected, disabled = self.option
            if not disabled:
                self.select[2].append((value if value is not None else label.strip(), selected))
            self.option = None

    def handle_endtag(self, tag):
        if tag in {"option", "select", "form"}:
            self.finish_option()
        if tag in {"select", "form"} and self.select:
            name, multiple, options = self.select
            values = [value for value, selected in options if selected]
            if not multiple:
                values = values[-1:] or [value for value, _ in options[:1]]
            self.form.fields.extend((name, value) for value in values)
            self.select = None
        if tag == "form":
            self.form = None

    def find(self, control):
        return next((form for form in self.forms if control in form.controls), None)


class LocalRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old, new = urlsplit(req.full_url), urlsplit(newurl)
        if (old.scheme, old.netloc) != (new.scheme, new.netloc):
            raise URLError("FS25 redirected outside the configured web endpoint")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Web:
    def __init__(self, endpoint, certificate=None):
        handlers = [ProxyHandler({}), HTTPCookieProcessor(CookieJar()), LocalRedirect()]
        if certificate is not None:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False  # The request targets a local IP, not the public hostname.
            context.verify_flags |= ssl.VERIFY_X509_PARTIAL_CHAIN
            context.load_verify_locations(cafile=str(certificate))
            handlers.append(HTTPSHandler(context=context))
        self.url = endpoint + "/index.html?lang=en"
        self.opener = build_opener(*handlers)

    def request(self, data=None, timeout=3):
        with self.opener.open(Request(self.url, data=data), timeout=timeout) as response:
            return response.read(4 * 1024 * 1024).decode("utf-8", "replace")

    def login(self, username, password, timeout=3):
        page = Forms(self.request(timeout=timeout))
        if page.find("start_server") or page.find("stop_server"):
            return page
        form = page.find("login") or page.find("username") or Form()
        self.request(form.payload(username=username, password=password, login="Login"), timeout)
        return Forms(self.request(timeout=timeout))


def start_payload(form, game_port, overrides):
    updates = {"start_server": "Start"}
    if "server_port" in form.controls:
        updates["server_port"] = str(game_port)
    for key, value in overrides.items():
        if key not in form.controls or value == "":
            continue
        if key == "crossplay_allowed":
            updates[key] = "on" if value == "true" else None
        else:
            updates[key] = value
    return form.payload(**updates)
