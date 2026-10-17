# Regional items

Builds `db/re/item_db_regional.yml` and `db/re/item_combos_regional.yml` from
official iRO and kRO client item tables.

The clients know items rAthena's item_db doesn't have: iRO's own event and
collaboration gear (the `*_US` items such as `23Anniv_Armor_US` or
`Hate_Ring2_US`) and kRO's newest releases. Without an entry the server treats
them as nonexistent: `@item` refuses them and no script can give them out.

## What it reads

| Input | From |
|---|---|
| `--iro` / `--kro` | the client's `itemInfo` table, Lua 5.1 bytecode (`System/iteminfo.lub`, `System/itemInfo_true.lub`, or `data/luafiles514/lua files/datainfo/iteminfo.lub` in the GRF). Repeat the flag; the first file that has an Id wins. |
| `--iro-moveinfo` / `--kro-moveinfo` | `data/itemmoveinfov5.txt`: trade rules, and AegisNames (iRO writes them as comments) |
| `--iro-skills` / `--kro-skills` | a folder with the client's `skillid.lub` and `skillinfolist.lub`, to turn skill names into skill constants |
| `kro_names_en.txt` | English names for kRO-only items (kRO's client only has Korean ones) |

Ids already in `db/re/item_db_{usable,equip,etc}.yml` are skipped, so after an
upstream merge a rerun drops whatever upstream has added since. The regional
file is imported first in `db/re/item_db.yml`, so an official entry with the
same Id also wins before the rerun.

## What it writes

For each item: type and subtype, slots, location, weight, attack / magic
attack / defense, weapon and armor level, required level, jobs and classes,
view, refineable / gradable, trade flags, and a script.

The script comes from the description (`bonus.py`): stats, damage modifiers
(size, race, class, property, ranged/melee, critical), cast time and delays,
skill damage, cooldowns and SP cost, enabled skills, autocasts on attack,
EXP / drop rates, HP gain on kill, indestructibility, all under refine, grade,
base level and stat conditions, in English and Korean. Set bonuses become
combos when their members can be found by name. Boxes become `getitem`
scripts (random and weighted ones included) when every item they hold can be
found.

Nothing is guessed. A line it can't read is written as a
`# <Id> untranslated: ...` comment above the item; a usable item with no
readable effect is written as Etc, so using it can't eat it. Run with
`--report report.md` for the list.

## Example

```sh
tools/regional_items/generate.py \
  --iro iRO/System/iteminfo.lub --iro iRO/System/iteminfo_sak.lub \
  --iro-moveinfo iro-grf/data/itemmoveinfov5.txt \
  --iro-skills "iro-grf/data/luafiles514/lua files/skillinfoz" \
  --kro "kro-grf/data/luafiles514/lua files/datainfo/iteminfo.lub" \
  --kro kRO/System/itemInfo_true.lub \
  --kro-moveinfo kro-grf/data/itemmoveinfov5.txt \
  --kro-skills "kro-grf/data/luafiles514/lua files/skillinfoz" \
  --report report.md
```

The client files are Gravity's and aren't part of this repository; extract the
GRF entries with any GRF tool.
