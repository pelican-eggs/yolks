# Yolks

A curated collection of core images that can be used with Pterodactyl's Egg system. Each image is rebuilt
periodically to ensure dependencies are always up-to-date.

Images are hosted on `ghcr.io` and exist under the `games`, `installers`, and `yolks` spaces. The following logic
is used when determining which space an image will live under:

* `games` — anything within the `games` folder in the repository. These are images built for running a specific game
or type of game.
* `installers` — anything living within the `installers` directory. These images are used by install scripts for different
Eggs within Pterodactyl, not for actually running a game server. These images are only designed to reduce installation time
and network usage by pre-installing common installation dependencies such as `curl` and `wget`.
* `yolks` — these are more generic images that allow different types of games or scripts to run. They're generally just
a specific version of software and allow different Eggs within Pterodactyl to switch out the underlying implementation. An
example of this would be something like Java or Python which are used for running bots, Minecraft servers, etc.

All of these images are available for `linux/amd64` and `linux/arm64` versions, unless otherwise specified, to use
these images on an arm system, no modification to them or the tag is needed, they should just work.

## Contributing

When adding a new version to an existing image, such as `java v42`, you'd add it within a child folder of `java`, so
`java/42/Dockerfile` for example. Please also update the correct `.github/workflows` file to ensure that this new version
is tagged correctly.

## Available Images

### [Oses](/oses)

* [alpine](/oses/alpine)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:alpine`
* [debian](/oses/debian)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:debian`
* [ubuntu](/oses/ubuntu)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:ubuntu`

### [Apps](/apps)

* [`uptimekuma`](/apps/uptimekuma)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:apps_uptimekuma`

### [Bot](/bot)

* [`bastion`](/bot/bastion)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:bot_bastion`
* [`parkertron`](/bot/parkertron)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:bot_parkertron`
* [`redbot`](/bot/red)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:bot_red`
* [`sinusbot`](/bot/sinusbot)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:bot_sinusbot`

### [Box64](/box64)

* [`Box64`](/box64)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:box64`

### [Bun](/bun)

* [`Bun Canary`](/bun/canary)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:bun_canary`
* [`Bun Latest`](/bun/latest)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:bun_latest`

### [Cassandra](/cassandra)

* [`cassandra_java8_python27`](/cassandra/cassandra_java8_python2)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:cassandra_java11_python2`
* [`cassandra_java11_python3`](/cassandra/cassandra_java11_python3)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:cassandra_java11_python3`

### [Dart](/dart)

* [`dart2.17`](/dart/2.17)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:dart_2.17`

### [dotNet](/dotnet)

* [`dotnet2.1`](/dotnet/2.1)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:dotnet_2.1`
* [`dotnet3.1`](/dotnet/3.1)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:dotnet_3.1`
* [`dotnet5.0`](/dotnet/5)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:dotnet_5`
* [`dotnet6.0`](/dotnet/6)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:dotnet_6`
* [`dotnet7.0`](/dotnet/7)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:dotnet_7`
* [`dotnet8.0`](/dotnet/8)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:dotnet_8`

### [Elixir](/elixir)

* [`elixir 1.12`](/elixir/1.12)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:elixir_1.12`
* [`elixir 1.13`](/elixir/1.13)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:elixir_1.13`
* [`elixir 1.14`](/elixir/1.14)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:elixir_1.14`
* [`elixir 1.15`](/elixir/1.12)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:elixir_1.15`
* [`elixir latest`](/elixir/latest)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:elixir_latest`

### [Erlang](/erlang)

* [`erlang22`](/erlang/22)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:erlang_22`
* [`erlang23`](/erlang/23)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:erlang_23`
* [`erlang24`](/erlang/24)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:erlang_24`

### [Games](/games)

* [`altv`](/games/altv)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/games:altv`
* [`arma3`](/games/arma3)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/games:arma3`
* [`dayz`](/games/dayz)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/games:dayz`
* [`minetest`](/games/minetest)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/games:minetest`  
* [`mohaa`](games/mohaa)
  * `ghcr.io/pterodactyl/games:mohaa`  
* [`Multi Theft Auto: San Andreas`](games/mta)
  * `ghcr.io/pterodactyl/games:mta`    
* [`samp`](/games/samp)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/games:samp`  
* [`source`](/games/source)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/games:source`
* [`valheim`](/games/valheim)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/games:valheim`

### [Golang](/go)

* [`go1.14`](/go/1.14)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:go_1.14`
* [`go1.15`](/go/1.15)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:go_1.15`
* [`go1.16`](/go/1.16)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:go_1.16`
* [`go1.17`](/go/1.17)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:go_1.17`
* [`go1.18`](/go/1.18)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:go_1.18`
* [`go1.19`](/go/1.19)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:go_1.19`
* [`go1.20`](/go/1.20)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:go_1.20`
* [`go1.21`](/go/1.21)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:go_1.21`

### [Java](/java)

* [`java8`](/java/8)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:java_8`
* [`java11`](/java/11)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:java_11`
* [`java16`](/java/16)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:java_16`
* [`java17`](/java/17)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:java_17`
* [`java19`](/java/19)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:java_19`
* [`java21`](/java/21)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:java_21`

### [MariaDB](/mariadb)

  * [`MariaDB 10.3`](/mariadb/10.3)
    * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:mariadb_10.3`
  * [`MariaDB 10.4`](/mariadb/10.4)
    * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:mariadb_10.4`
  * [`MariaDB 10.5`](/mariadb/10.5)
    * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:mariadb_10.5`
  * [`MariaDB 10.6`](/mariadb/10.6)
    * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:mariadb_10.6`
  * [`MariaDB 10.7`](/mariadb/10.7)
    * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:mariadb_10.7`
  * [`MariaDB 11.2`](/mariadb/11.2)
    * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:mariadb_11.2`

### [MongoDB](/mongodb)

  * [`MongoDB 4`](/mongodb/4)
    * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:mongodb_4`
  * [`MongoDB 5`](/mongodb/5)
    * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:mongodb_5`
 * [`MongoDB 6`](/mongodb/6)
    * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:mongodb_6`    
 * [`MongoDB 7`](/mongodb/7)
    * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:mongodb_7`

### [Mono](/mono)

* [`mono_latest`](/mono/latest)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:mono_latest`

### [Nodejs](/nodejs)

* [`node12`](/nodejs/12)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:nodejs_12`
* [`node14`](/nodejs/14)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:nodejs_14`
* [`node16`](/nodejs/16)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:nodejs_16`
* [`node17`](/nodejs/17)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:nodejs_17`
* [`node18`](/nodejs/18)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:nodejs_18`
* [`node19`](/nodejs/19)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:nodejs_19`
* [`node20`](/nodejs/20)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:nodejs_20`
* [`node21`](/nodejs/21)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:nodejs_21`

### [PostgreSQL](/postgres)

  * [`Postgres 9`](/postgres/9)
    * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:postgres_9`
  * [`Postgres 10`](/postgres/10)
    * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:postgres_10`
  * [`Postgres 11`](/postgres/11)
    * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:postgres_11`
  * [`Postgres 12`](/postgres/12)
    * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:postgres_12`
  * [`Postgres 13`](/postgres/13)
    * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:postgres_13`
  * [`Postgres 14`](/postgres/14)
    * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:postgres_14`  

### [Python](/python)

* [`python3.7`](/python/3.7)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:python_3.7`
* [`python3.8`](/python/3.8)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:python_3.8`
* [`python3.9`](/python/3.9)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:python_3.9`
* [`python3.10`](/python/3.10)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:python_3.10`
* [`python3.11`](/python/3.11)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:python_3.11`
* [`python3.12`](/python/3.12)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:python_3.12`

### [Redis](/redis)

  * [`Redis 5`](/redis/5)
    * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:redis_5`
  * [`Redis 6`](/redis/6)
    * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:redis_6`
  * [`Redis 7`](/redis/7)
    * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:redis_7`

### [Rust](/rust)

* ['rust1.56'](/rust/1.56)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:rust_1.56`
* ['rust1.60'](/rust/1.60)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:rust_1.60`
* ['rust latest'](/rust/latest)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:rust_latest`

### [SteamCMD](/steamcmd)
* [`SteamCMD Debian lastest`](/steamcmd/debian)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/steamcmd:debian`
* [`SteamCMD Debian Dotnet`](/steamcmd/dotnet)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/steamcmd:dotnet`
* [`SteamCMD Proton`](/steamcmd/proton)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/steamcmd:proton`
* [`SteamCMD Ubuntu latest LTS`](/steamcmd/ubuntu)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/steamcmd:ubuntu`

### [Voice](/voice)
* [`Mumble`](/voice/mumble)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:voice_mumble`
* [`TeaSpeak`](/voice/teaspeak)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:voice_teaspeak`

### [Wine](/wine)

* [`Wine`](/wine)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:wine_latest`
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:wine_devel`
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/yolks:wine_staging`

### [Installation Images](/installers)

* [`alpine-install`](/installers/alpine)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/installers:alpine`
* [`debian-install`](/installers/debian)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/installers:debian`
* [`ubuntu-install`](/installers/ubuntu)
  * `registry.cn-hangzhou.aliyuncs.com/jiongzu/installers:ubuntu`
