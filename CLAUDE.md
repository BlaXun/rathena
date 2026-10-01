# Working in this repository

This is **Flux159/rathena**, the rAthena fork that [Ragnarok Offline](https://github.com/Flux159/ragnarokoffline.app) builds its game servers from. It is not upstream rAthena.

## Pull requests go to `ragnarokoffline`, not `master`

| Branch | What it is | Open PRs against it? |
|---|---|---|
| `ragnarokoffline` | The fork's own branch. The app pins commits on it (`config/VENDOR_PINS` in the app repo). | **Yes. Every PR goes here.** |
| `master` | A mirror of upstream rAthena's `master`. | **No.** |

GitHub may suggest `master` as the base, because that is the repository's default branch. Change it to `ragnarokoffline` before you open the PR. A PR against `master` drags in every upstream commit that `ragnarokoffline` hasn't merged yet: hundreds of unrelated commits and files.

How to work:
- Branch from `ragnarokoffline`: `git fetch origin && git switch -c my-change origin/ragnarokoffline`.
- Keep a PR to one change. Personal tooling, editor settings and unrelated deletions belong in their own PR, or nowhere.
- `ragnarokoffline` only moves forward. Releases pin commits on it, so it refuses force-pushes and is never rebased. Newer upstream comes in as a merge of `master` into it, in its own PR.
- To bring your branch up to date, merge or rebase onto `origin/ragnarokoffline`, never onto `master`.

## What belongs here

Fixes to rAthena itself, and the fork's extension points:
- **Lua hooks** (`src/map/skill_lua.cpp`, `.hpp`): `skill(...)` and `item(...)` hooks with a priority chain, `c:cast`, drain, heal and status actions. Mods' `lua/` folders use these.
- **Server extensions** (`db/extension_db.yml`): fork behaviour a mod can switch on, with typed values. `@extensions` lists them in game. **Read [doc/extensions.md](doc/extensions.md) before changing stock behaviour:** a change that should be optional belongs behind an extension (off by default), not in a core edit.
- Script commands and events mods rely on, e.g. `makeitemowned`, `OnPCDropItemEvent`, and the one-time login tokens.

App-specific additions (the population engine, the stylist, crash tracing) are not here. They are patches in the app repo (`third-party/`, `scripts/apply-server-mods.sh`), applied on top of this branch at build time. Anything you change here must still let those patches apply.

## Conventions

- Follow upstream rAthena conventions: coding style, the YAML DB layout, the pre-renewal/renewal split (`db/pre-re`, `db/re`, `src/config/renewal.hpp`), @command patterns.
- **A schema change** goes in `sql-files/main.sql` *and* a new `sql-files/upgrades/upgrade_YYYYMMDD.sql`. The app's supervisor also applies its own idempotent migration at start-up; see `ensure_*` in the app's `stack/src/`.
- **Prefer an extension or a Lua hook** to changing stock behaviour unconditionally. Keep any core edit small, so upstream merges stay easy.

## Checking a change

- Build: `./configure && make server`, or CMake (`cmake -B build && cmake --build build`). Add `--enable-prere` for pre-renewal.
- A quick compile check of one file: `c++ -std=c++20 -fsyntax-only -Isrc -I3rdparty -I3rdparty/rapidyaml/src -I3rdparty/rapidyaml/ext/c4core/src -I3rdparty/libconfig -I3rdparty/lua -I3rdparty/httplib -I3rdparty/json/include -I3rdparty/yaml-cpp/include -I3rdparty/mysql/include -I3rdparty/pcre/include -I3rdparty/zlib/include <file>`.
- CI builds gcc, clang, CMake, MSBuild, the modes and packet versions, and loads the NPCs and YAML DBs. The two macOS Homebrew build jobs are known to fail on this fork, for reasons unrelated to the change being tested.
- To test inside the app, point its `config/VENDOR_PINS` at your commit. The app's `docs/FORKS.md` covers the whole flow.
