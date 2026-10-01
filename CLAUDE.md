# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## This repository is a fork

This is BlaXun's rAthena fork (`origin` → `github.com/BlaXun/rathena`), tracking a Flux159 branch (`ragnarokoffline`) on top of upstream rAthena. The fork's own additions live on topic branches that are merged forward from `master`; recent ones include `extensions-framework`, `lua-skill-hooks`, `lua-item-hooks`, `makeitem-owned`, `mob-drop-item-event`, `mob-db-partial-drop-override`. Default branch is `master`.

Treat upstream rAthena conventions (coding style, YAML DB layout, @command patterns, pre-re/renewal split) as the ground truth; fork-specific features layer on top via two mechanisms described below (extensions, Lua hooks), designed to add behaviour **without** fighting an upstream merge.

## Build

MySQL is required at build time — the Makefile short-circuits every server target to `needs_mysql` if `configure` did not find it.

**Autotools (Linux):**
```
./configure                   # add --enable-prere for pre-renewal; see src/config/renewal.hpp
make server                   # builds common, login, char, map, web (if enabled) + the conf/db/import folders
make clean server             # from scratch
make tools                    # mapcache etc. (src/tool and src/map tools)
```

**CMake (cross-platform):**
```
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo ..
cmake --build . -j
```

**Windows:** open `rAthena.sln` in Visual Studio 2017+.

**Docker dev env:** `cd tools/docker && docker-compose up -d && docker-compose run builder bash` — runs `./configure && make` inside a Linux container with MySQL on port 3306 (creds: `ragnarok` / `ragnarok`).

**Pre-re vs renewal** is a compile-time switch controlled by `src/config/renewal.hpp` (uncomment `#define PRERE`, or pass `--enable-prere` to `configure`). Changing modes requires a rebuild and a different DB directory (`db/pre-re` vs `db/re`).

## Running

```
./athena-start start|stop|restart|status
```
Launches `login-server`, `char-server`, `map-server` (and `web-server` if built). Server binaries land in the repo root; PID files are hidden dotfiles. There is no package manager / lockfile — the running set is whatever `make server` just linked.

CI (`.github/workflows/*.yml`) runs the same `make server` / cmake builds across gcc, clang, MSBuild, plus modes (`PRERE`), packet-version matrices, and VIP builds — mirror these flags locally before claiming a cross-mode change compiles. `npc_db_validation.yml` loads NPCs and the YAML DBs — breaking either shape is a CI-visible regression.

## Code layout

- `src/common/` — DB abstraction, YAML (`TypesafeYamlDatabase`), socket, timers, logging, shared types (`mmo.hpp`).
- `src/login/`, `src/char/`, `src/map/` — the three server binaries. `src/map/` is by far the largest (~100 files); most feature work lives here.
- `src/web/` — optional HTTP server (needs yaml-cpp, httplib).
- `src/tool/` — mapcache + helpers.
- `src/custom/` — upstream convention for user hooks (`#include "custom/*.inc"` from the main sources). **Prefer the Extensions / Lua mechanisms below over editing core files.**
- `src/config/` — compile-time switches (renewal, packet version, max HP/SP, etc.).
- `3rdparty/` — libconfig, rapidyaml, yaml-cpp, httplib, **and lua** (vendored Lua 5.4).
- `conf/` — runtime config (`*.conf`, `*.yml`).
- `db/` → `db/pre-re/` and `db/re/` with mode-specific YAML; shared YAML sits in `db/`.
- `npc/` — stock NPC scripts (`npc/custom/` for user scripts).
- `sql-files/` — schema; imported on first Docker start.

## The two layering mechanisms (fork-specific)

The fork's design rule is: **a merged change does nothing by default**. New behaviour sits behind one of these two gates so a stock operator sees stock rAthena, and an upstream merge never fights an extension's YAML or a mod's Lua.

### 1. Extensions framework — `src/map/extensions.{cpp,hpp}` + `db/extension_db.yml`

A named on/off switch (plus optional typed values) registered in `db/extension_db.yml`. Code that deviates from stock reads it as:

```cpp
if (extension_enabled("pc_drop_item_event")) { ... }
int64 rate = extension_int("my_feature", "rate", /*fallback=*/100);
```

While the flag is off, the caller sees `false` / the stock fallback — so merging an extension is inert until a server operator (or a mod) ships an override in `db/import/extension_db.yml` with `Enabled: true`. Script side: `getextension("id")` and `getextensionvalue("id","key"{,stock})`. In-game: `@extensions` lists them, `@extensioninfo <id>` prints metadata.

**When adding a feature that deviates from stock:** add an entry in `db/extension_db.yml` and gate the C++ with `extension_enabled()` / `extension_int()`. Do not flip the default to `true`.

### 2. Lua skill/item hooks — `src/map/skill_lua.{cpp,hpp}` + `src/map/lua_vm.cpp`

Lua 5.4 is compiled directly into the map server as **one translation unit** (`lua_vm.cpp` `#include`s the `.c` files — no new build target). At startup, every `.lua` in `db/import/lua/` (or the files listed in `db/import/lua/load.txt`) is run in a sandbox with no `io`/`os`/`package`/`debug`. Scripts register hooks either:

- `skill("MG_FIREBOLT", { priority = 5, ratio = fn, hit = fn, element = fn, on_hit = fn })` — wraps a skill's class (`src/map/skills/`), composes across mods in priority order.
- `item("VORPAL_BLADE", { priority = 5, on_attack = fn, on_hit_taken = fn })` — fires on every attack by/against a unit with the item equipped, after damage calc, regardless of skill or weapon direction.

Hooks are chained across mods (every registration runs, ties broken by load order); each hook receives the previous one's result as `stock` for `ratio`/`hit`/`element`. `on_hit` queues drain/heal/status/polymorph actions that `skill_lua_apply` executes after the hit is dealt — so a hook never operates on a dead-but-not-yet-removed target. Memory (64 MiB) and instruction budgets (1k/call, 20k/file) exist so a runaway hook disables itself with a log line rather than crashing the server.

See the big block comment at the top of `src/map/skill_lua.hpp` — it's the canonical hook reference.

**When adding a formula tweak or an item effect:** prefer a Lua hook over editing `battle.cpp` / `skill.cpp`. Only reach for C++ when the hook API genuinely cannot express it.

## Database and config override pattern

Every YAML DB has an **import layer**: files in `db/import/` override entries in `db/`, and `conf/import/` overrides `conf/`. The templates for first-time setup live in `db/import-tmpl/` and `conf/import-tmpl/` and are copied by `make import` (also run as part of `make server`). This is upstream rAthena convention — the extension and Lua mechanisms above both lean on it (`db/import/extension_db.yml`, `db/import/lua/`).

Server operators and mods **never edit the base files**; everything goes through `import/`. When adding a new DB entry that should ship with the fork, put it in the appropriate base file; when adding something that is only meaningful if an operator opts in, document it as an import override.

## Conventions worth knowing

- **Tabs** in `.cpp`/`.hpp`/`.c`/`.h` and in `npc/**/*.txt`; **4-space YAML**. `.editorconfig` enforces it.
- **C++17**, no exceptions in the core (except where Lua needs them — `lua_vm.cpp` compiles the Lua `.c` as C++ specifically so its errors become exceptions instead of `longjmp` across C++ frames).
- Typed YAML DBs derive from `TypesafeYamlDatabase<Key, Struct>` in `src/common/database.hpp` and override `parseBodyNode`; mirror an existing one (e.g. `ExtensionDatabase`) when adding a new DB.
- `@commands` live in `src/map/atcommand.cpp`; permissions in `conf/atcommands.yml` + `conf/groups.yml`.
- Script commands are registered in the big table at the bottom of `src/map/script.cpp`; documentation lives in `doc/script_commands.txt` and MUST be updated when adding one.
- Attribution lines in commits/PRs follow the system reminder in effect at the time; current fork style (see `git log --oneline`) is a short imperative subject with a tag prefix (`Lua:`, `extensions:`, `script:`).
