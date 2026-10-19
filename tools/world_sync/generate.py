#!/usr/bin/env python3
"""Fill the renewal world from the official clients' navigation tables.

The clients' navigation data (data/luafiles514/lua files/navigation/navi_*.lub,
iRO's _us and kRO's _krpri) lists every map's monsters (with counts), NPCs
(name, sprite, position) and links (warp portals and NPC transports). This
compares it with what the renewal server loads. It only fills maps rAthena
does nothing with: the maps it adds, and rAthena's maps that have no spawn
line anywhere in npc/ (loaded or not, commented out or not), no NPCs, no
portals and no script warps (e.g. Biosphere, Jormungandr). Everything rAthena
spawns, scripts, gates or turned off stays rAthena's.

  db/map_index.txt, conf/maps_athena.conf
      the maps the clients have and the server doesn't, in a generated block
      at the end, rewritten on every run
  db/re/map_cache.dat
      their cells, read from the GRF's .gat (and the water level from its
      .rsw) as tools/mapcache does; never the shared db/map_cache.dat
  npc/re/world_sync/spawns.txt
      the clients' monsters on those maps (whole-map spawns at the clients'
      counts; MVPs one per hour, boss-class monsters three at most, slowly)
  npc/re/world_sync/warps.txt, transports.txt
      portals and "talk to travel" links out of those maps
  npc/re/world_sync/npcs.txt
      Kafras and tool shops on those maps
  --entrances FILE
      links from rAthena's maps into those maps, for an opt-in mod: a player
      whose client lacks a new map would hang on its loading screen
  --placeholders FILE
      every other NPC the clients place, with its sprite, name and spot and a
      greeting (their dialog and logic aren't in any client data), for an
      optional mod; also the client's signboards that mark an NPC nobody places

Monsters missing from the monster db aren't spawned (listed in the report);
monsters only scripts summon (E_, G_, MD_, ...) are skipped. After an
upstream merge run prune.py (no client data needed), or rerun this.
"""
import argparse
import collections
import json
import os
import re
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import luadata  # noqa: E402

SKIP_MAPS = {'null', 'monk_test'}
MARK = '//------------------------- World sync (generated) ---------------------------'
EVENT_MAP = re.compile(r'evt|event|race|arena|gld|^guild_|^gvg|^pvp|^que_')
# monsters that only scripts, instances or events summon (E_ event, G_ summoned, MD_ instance, ...)
SCRIPT_MOB = re.compile(r'^(?:E_|G_|MD_|EVENT_|HIDDEN|DUMMY|TEST|C\d_)|_DUMMY|_TEST$')
SPAWN_LINE = re.compile(r'^\s*(?://+|/\*)?\s*([a-z0-9_@.\-]+),\d+,\d+(?:,\d+,\d+)?\t+(?:boss_|miniboss_)?monster\t', re.I)
SCRIPT_WARP = re.compile(r'\bwarp\s*\(?\s*"([a-z0-9_@.\-]+)"', re.I)
SCRIPT_SPAWN = re.compile(r'\b(?:area)?monster\s*\(?\s*"([a-z0-9_@.\-]+)"', re.I)
INVISIBLE = {111, 139, 844, 10252}            # hidden / trigger sprites
HDR = re.compile(r'^([a-z0-9_@.\-]+)(?:,(\d+),(\d+)(?:,(\d+))?(?:,\d+)*)?\t+'
                 r'(script|shop|cashshop|itemshop|pointshop|marketshop|warp|warp2|monster|boss_monster|'
                 r'miniboss_monster|duplicate\([^)]*\))\t+([^\t]+)\t*([^\t{]*)', re.I)


# ------------------------------------------------------------------ server side

def server_world(root):
    files, deleted, seen = [], set(), set()

    def conf(path):
        if path in seen or not os.path.exists(os.path.join(root, path)):
            return
        seen.add(path)
        for line in open(os.path.join(root, path), errors='replace'):
            m = re.match(r'(npc|import|delnpc):\s*(\S+)', line.split('//')[0].strip())
            if not m:
                continue
            if m.group(1) == 'import':
                conf(m.group(2))
            elif m.group(1) == 'npc':
                files.append(m.group(2))
            else:
                deleted.add(m.group(2))
    conf('npc/re/scripts_main.conf')
    npcs, mobs, warps = [], collections.defaultdict(set), []
    for f in dict.fromkeys(files):
        if f in deleted or '/world_sync/' in f:
            continue
        p = os.path.join(root, f)
        if not os.path.exists(p):
            continue
        for line in open(p, errors='replace'):
            m = HDR.match(line)
            if not m:
                continue
            mp, x, y, d, kind, name, rest = m.groups()
            kind = kind.lower()
            if 'monster' in kind:
                mm = re.match(r'\s*(\d+)', rest)
                if mm:
                    mobs[mp.lower()].add(int(mm.group(1)))
            elif kind.startswith('warp'):
                warps.append((mp.lower(), int(x or 0), int(y or 0), rest.split(',')[2].lower() if rest.count(',') >= 2 else ''))
            else:
                npcs.append((mp.lower(), int(x or 0), int(y or 0), name.split('::')[0].split('#')[0].strip().lower()))
    maps, ours = set(), set()
    conf_text = open(os.path.join(root, 'conf', 'maps_athena.conf'), errors='replace').read()
    official_text, _, ours_text = conf_text.partition(MARK)
    for m in re.finditer(r'^map:\s*(\S+)', official_text, re.M):
        maps.add(m.group(1).lower())
    for m in re.finditer(r'^map:\s*(\S+)', ours_text, re.M):
        ours.add(m.group(1).lower())
    mobdb, mobclass = {}, {}
    for f in ('db/re/mob_db_world.yml', 'db/re/mob_db.yml', 'db/import/mob_db.yml'):
        p = os.path.join(root, f)
        if os.path.exists(p):
            t = open(p, encoding='utf-8').read()
            for e in re.split(r'\n(?=  - Id: )', t):
                m = re.match(r'  - Id: (\d+)\s*\n    AegisName: (\S+)', e)
                if m:
                    mobdb[int(m.group(1))] = m.group(2)
                    mobclass[int(m.group(1))] = 'mvp' if '\n    MvpExp:' in e else \
                        'boss' if re.search(r'\n    Class: Boss', e) else 'normal'
    return maps, ours - maps, npcs, mobs, warps, mobdb, mobclass


def touched_maps(root):
    """Maps rAthena decides the monsters of: any spawn line for them anywhere in npc/ (loaded or
    not, commented out or not: upstream turns spawns off on purpose), any script or instance that
    summons monsters on them, and the instance maps. Also returns the maps scripts warp to."""
    touched, warped = set(), set()
    for base, _, fns in os.walk(os.path.join(root, 'npc')):
        if os.sep + 'world_sync' in base:
            continue
        for fn in fns:
            if not fn.endswith('.txt'):
                continue
            for line in open(os.path.join(base, fn), errors='replace'):
                m = SPAWN_LINE.match(line)
                if m:
                    touched.add(m.group(1).lower())
                for m in SCRIPT_SPAWN.finditer(line):
                    touched.add(m.group(1).lower())
                for m in SCRIPT_WARP.finditer(line):
                    warped.add(m.group(1).lower())
    p = os.path.join(root, 'db', 're', 'instance_db.yml')
    if os.path.exists(p):
        for m in re.finditer(r'^\s+(?:Map:\s*|-\s*Map:\s*)?([a-z0-9_@.\-]+)(?::\s*true)?\s*$',
                             open(p, encoding='utf-8').read(), re.M):
            if '@' in m.group(1):
                touched.add(m.group(1).lower())
        for m in re.finditer(r'Map:\s*([a-z0-9_@.\-]+)', open(p, encoding='utf-8').read()):
            touched.add(m.group(1).lower())
    return touched, warped


# ------------------------------------------------------------------ client side

def navi(dirs):
    """Rows from every navi table found, iRO first."""
    out = collections.defaultdict(list)
    for d, enc, tag in dirs:
        for kind in ('mob', 'npc', 'link'):
            for suffix in ('_us', '_krpri', ''):
                p = os.path.join(d, 'navi_%s%s.lub' % (kind, suffix))
                if os.path.exists(p):
                    key = 'Navi_' + kind.capitalize()
                    rows = luadata.ordered_lines(luadata.run([p], enc).get(key) or {})
                    out[kind] += [(tag, r) for r in rows if isinstance(r, dict)]
                    break
    return out


class Grfs:
    def __init__(self, paths):
        sys.path.insert(0, HERE)
        import grf_reader
        self.grfs = [grf_reader.GRF(p) for p in paths]
        self.encrypted = set()

    def read(self, name):
        for g in self.grfs:
            for k in (name, name.lower()):
                if k in g.index:
                    try:
                        return g.read(k)
                    except ValueError:      # DES-encrypted entry (old GRFs)
                        self.encrypted.add(name)
        return None


def map_cells(grfs, name):
    gat = grfs.read('data\\%s.gat' % name)
    if not gat or gat[:4] != b'GRAT':
        return None
    xs, ys = struct.unpack_from('<II', gat, 6)
    water = None
    rsw = grfs.read('data\\%s.rsw' % name)
    if rsw and rsw[:4] == b'GRSW':
        ver = (rsw[4] << 8) | rsw[5]
        if 0x104 <= ver <= 0x205:        # same versions as rAthena's mapcache
            off = 171 if ver >= 0x205 else 167 if ver >= 0x202 else 166
            water = int(struct.unpack_from('<f', rsw, off)[0])
    cells = bytearray(xs * ys)
    off = 14
    for i in range(xs * ys):
        height = struct.unpack_from('<f', gat, off)[0]
        typ = struct.unpack_from('<I', gat, off + 16)[0]
        off += 20
        if typ == 0 and water is not None and height > water:
            typ = 3
        cells[i] = typ & 0xFF
    return xs, ys, bytes(cells)


def cached(path):
    if not os.path.exists(path):
        return set()
    data = open(path, 'rb').read()
    _, count = struct.unpack_from('<IH', data, 0)
    have, off = set(), 8
    for _ in range(count):
        name, xs, ys, ln = struct.unpack_from('<12shhi', data, off)
        have.add(name.split(b'\0')[0].decode())
        off += 20 + ln
    return have


def set_block(path, lines):
    """Rewrite the generated block at the end of a list file (nothing appended twice)."""
    t = open(path, encoding='utf-8', errors='surrogateescape').read()
    t = t.split('\n' + MARK)[0].rstrip('\n') + '\n'
    if lines:
        t += '\n' + MARK + '\n' + ''.join(lines)
    open(path, 'w', encoding='utf-8', errors='surrogateescape', newline='\n').write(t)


def add_to_cache(path, maps):
    if not os.path.exists(path):
        open(path, 'wb').write(struct.pack('<IH', 8, 0) + b'\0\0')
    data = bytearray(open(path, 'rb').read())
    size, count = struct.unpack_from('<IH', data, 0)
    have, off = set(), 8
    for _ in range(count):
        name, xs, ys, ln = struct.unpack_from('<12shhi', data, off)
        have.add(name.split(b'\0')[0].decode())
        off += 20 + ln
    added = 0
    for name, (xs, ys, cells) in maps.items():
        if name in have:
            continue
        z = zlib.compress(cells)
        data += struct.pack('<12shhi', name.encode()[:12], xs, ys, len(z)) + z
        count += 1
        added += 1
    struct.pack_into('<IH', data, 0, len(data), count)
    open(path, 'wb').write(bytes(data))
    return added


def other_npcs(dirs):
    """(map, x, y, name) of the NPCs in more script folders."""
    out = []
    for d in dirs:
        for base, _, fns in os.walk(d):
            for fn in fns:
                if not fn.endswith('.txt'):
                    continue
                for line in open(os.path.join(base, fn), errors='replace'):
                    m = HDR.match(line)
                    if m and m.group(2) and not m.group(5).lower().startswith('warp') and 'monster' not in m.group(5).lower():
                        out.append((m.group(1).lower(), int(m.group(2)), int(m.group(3)), m.group(6).lower()))
    return out


# ------------------------------------------------------------------ output

def esc(s):
    return s.replace('"', "'").replace('\t', ' ').strip()


TOOLS = [501, 502, 503, 504, 506, 525, 601, 602, 645, 656, 1065, 611, 713, 1750]


def service_script(role, n, mp, x, y):
    """A working body for the NPC roles every town has."""
    if role == 'kafra':
        return ('\tcutin "kafra_01",2;\n\tcallfunc "F_Kafra",0,1,1,40,700;\n'
                '\tsavepoint "%s",%d,%d,1,1;\n\tcallfunc "F_KafEnd",0,1,"here";\n' % (mp, x, y))
    if role == 'locker':
        return '\tmes "[%s]";\n\tmes "Your storage is open.";\n\tclose2;\n\topenstorage;\n\tend;\n' % n
    if role == 'guild':
        return ('\tmes "[%s]";\n\tif (!getcharid(2)) {\n\t\tmes "Only guild members can use the guild storage.";\n'
                '\t\tclose;\n\t}\n\tmes "Here is your guild\'s storage.";\n\tclose2;\n\tguildopenstorage;\n\tend;\n' % n)
    return None


def npc_role(name):
    low = name.lower()
    if re.search(r'kafra (?:employee|transport|staff|service)', low):
        return 'kafra'
    if re.fullmatch(r'tool (?:dealer|merchant|shop)', low):
        return 'tools'
    return None                                  # storage stays with the Kafras (and their fee)


def npc_name(s):
    s = re.sub(r'[^\w &\'().\-가-힣]', '', s).strip()
    return s or 'Npc'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rathena', default=os.path.join(HERE, '..', '..'))
    ap.add_argument('--iro-navi', help='folder with navi_*_us.lub')
    ap.add_argument('--kro-navi', help='folder with navi_*_krpri.lub')
    ap.add_argument('--grf', action='append', default=[], help='GRFs to read map cells from, most recent first')
    ap.add_argument('--other-npcs', action='append', default=[],
                    help='more NPC script folders the server loads (e.g. the app\'s npc/mods); only used to keep '
                         'new NPCs from standing on top of theirs')
    ap.add_argument('--signboards', help="the client's signboardlist.lub (markers for NPCs the server lacks)")
    ap.add_argument('--placeholders', help='write the NPCs that only greet (no logic yet) to this file, '
                                           'e.g. for a mod; without it they are left out')
    ap.add_argument('--entrances', help="write the links from rAthena's maps into the maps world sync fills "
                                        "to this file, for an opt-in mod (players need those maps in their client)")
    ap.add_argument('--report')
    a = ap.parse_args()
    root = os.path.abspath(a.rathena)

    maps, ours, s_npcs, s_mobs, s_warps, mobdb, mobclass = server_world(root)
    touched, warped = touched_maps(root)
    dirs = [(d, enc, tag) for d, enc, tag in ((a.iro_navi, 'latin-1', 'iRO'), (a.kro_navi, 'cp949', 'kRO')) if d]
    nv = navi(dirs)
    report = collections.defaultdict(list)

    # --- maps
    client_maps = set()
    for tag, r in nv['mob'] + nv['npc'] + nv['link']:
        client_maps.add(str(r.get(1, '')).lower())
        if r.get(9):
            client_maps.add(str(r[9]).lower())
    grfs = Grfs(a.grf) if a.grf else None
    if grfs:
        # every map the GRFs carry, not only the ones the navigation mentions
        for g in grfs.grfs:
            for k in g.index:
                m = re.fullmatch(r'data\\([^\\]+)\.rsw', k, re.I)
                if m:
                    client_maps.add(m.group(1).lower())
    new_maps = {}
    for mp in sorted(client_maps - maps - ours - SKIP_MAPS):
        if not re.fullmatch(r'[a-z0-9_@.\-]{1,11}', mp) or grfs is None:
            continue
        c = map_cells(grfs, mp)
        if c:
            new_maps[mp] = c
        elif 'data\\%s.gat' % mp in grfs.encrypted:
            report['maps whose .gat is DES-encrypted (skipped)'].append(mp)
        else:
            report['maps without .gat in the GRFs'].append(mp)
    world = ours | set(new_maps)                 # the maps world sync adds
    loaded = maps | world
    # maps world sync may fill: its own, and rAthena's that rAthena does nothing with (listed, but
    # no spawns anywhere, no NPCs, no portals, no script warps: e.g. Biosphere, Jormungandr)
    used = touched | warped | {n[0] for n in s_npcs} | {w[0] for w in s_warps} | {w[3] for w in s_warps}
    fillable = world | {m for m in maps if m not in used}

    # --- spawns
    want = collections.defaultdict(dict)
    boss = set()
    for tag, r in nv['mob']:
        mp = str(r.get(1, '')).lower()
        if mp in SKIP_MAPS or mp not in loaded or not r.get(4):
            continue
        mid, cnt = r[4] & 0xFFFF, r[4] >> 16
        aegis = str(r.get(6, ''))
        if not mid or SCRIPT_MOB.search(aegis) or SCRIPT_MOB.search(mobdb.get(mid, '')):
            continue
        if mp not in fillable or EVENT_MAP.search(mp) or '@' in mp:
            # rAthena (or a script, instance or event) decides this map's monsters
            report['spawns left to rAthena (map it spawns, scripts or turned off)'].append('%s %d' % (mp, mid))
            continue
        want[mp][mid] = max(cnt, want[mp].get(mid, 0), 1)
        if r.get(3) == 301:
            boss.add((mp, mid))
    spawns = []
    for mp in sorted(want):
        for mid, cnt in sorted(want[mp].items()):
            if mid in s_mobs.get(mp, set()):
                continue
            if mid not in mobdb:
                report['monsters not in the monster db (not spawned)'].append('%s %d' % (mp, mid))
                continue
            kind = mobclass.get(mid)
            if kind == 'mvp' or (mp, mid) in boss:
                spawns.append('%s,0,0\tboss_monster\t--ja--\t%d,1,3600000,600000,0' % (mp, mid))
            elif kind == 'boss':
                # boss-class field monsters: few and slow, as rAthena spawns them
                spawns.append('%s,0,0\tmonster\t--ja--\t%d,%d,1800000,600000,0' % (mp, mid, min(cnt, 3)))
            else:
                spawns.append('%s,0,0\tmonster\t--ja--\t%d,%d,5000,0,0' % (mp, mid, cnt))

    # --- warps and transports
    def has_warp(mp, x, y, dest):
        # a portal within 5 cells, a portal to the same map within 15, or a
        # script NPC at the spot (rAthena builds many doors as NPCs)
        return any(w[0] == mp and ((abs(w[1] - x) <= 5 and abs(w[2] - y) <= 5) or
                                   (w[3] == dest and abs(w[1] - x) <= 15 and abs(w[2] - y) <= 15)) for w in s_warps) \
            or any(n[0] == mp and abs(n[1] - x) <= 2 and abs(n[2] - y) <= 2 for n in s_npcs)

    def has_npc(mp, x, y, name=''):
        n = re.sub(r'[^a-z0-9가-힣]', '', name.lower())
        return any(s[0] == mp and ((abs(s[1] - x) <= 3 and abs(s[2] - y) <= 3) or (n and re.sub(r'[^a-z0-9가-힣]', '', s[3]) == n))
                   for s in s_npcs)

    warps, transports, entrances, seen = [], [], [], set()
    for tag, r in nv['link']:
        src, dst = str(r.get(1, '')).lower(), str(r.get(9, '')).lower()
        x, y, dx, dy, typ = r.get(7, 0), r.get(8, 0), r.get(10, 0), r.get(11, 0), r.get(3)
        if src not in loaded or dst not in loaded or (src, x, y) in seen:
            continue
        if src not in fillable or (src not in world and dst in world):
            # rAthena's maps keep rAthena's links: its NPCs gate many behind quests and fees, and
            # a link into a map the player's client may lack would strand them. Entrances into
            # the maps world sync fills go to --entrances (an opt-in mod) instead.
            if dst in fillable and not has_warp(src, x, y, dst):     # also: every map -> a map only world sync adds
                entrances.append('%s,%d,%d,0\twarp\tws_%s_%d\t1,1,%s,%d,%d' % (src, x, y, src, r.get(2, 0), dst, dx, dy))
            else:
                report['links left to rAthena (from a map it already uses)'].append('%s -> %s' % (src, dst))
            continue
        seen.add((src, x, y))
        if typ == 200 and not has_warp(src, x, y, dst):
            warps.append('%s,%d,%d,0\twarp\tws_%s_%d\t1,1,%s,%d,%d' % (src, x, y, src, r.get(2, 0), dst, dx, dy))
        elif typ == 201 and not has_npc(src, x, y) and not has_warp(src, x, y, dst):
            label = esc(str(r.get(5) or r.get(6) or dst))
            transports.append('%s,%d,%d,4\tscript\tTravel to %s#ws%d\t4W_SAILOR,{\n'
                              '\tmes "[Guide]";\n\tmes "Shall I take you to ^0000FF%s^000000?";\n'
                              '\tif (select("Yes, please.:No, thanks.") == 2) close;\n'
                              '\tclose2;\n\twarp "%s",%d,%d;\n\tend;\n}' % (src, x, y, dst[:14], r.get(2, 0), dst, dst, dx, dy))

    # --- NPCs
    names_en = {}
    nf = os.path.join(HERE, 'kro_npc_names_en.txt')
    if os.path.exists(nf):
        for line in open(nf, encoding='utf-8'):
            if '\t' in line and not line.startswith('#'):
                k, v = line.rstrip('\n').split('\t', 1)
                names_en[k.strip()] = v.strip()
    positions = {}
    pf = os.path.join(HERE, 'npc_positions.txt')
    if os.path.exists(pf):
        for line in open(pf, encoding='utf-8'):
            m = re.match(r'\s*(\d+)\s+([a-z0-9_@.\-]+)\s+(\d+)\s+(\d+)', line)
            if m:
                positions[int(m.group(1))] = (m.group(2), int(m.group(3)), int(m.group(4)))
    scripted = {n[0] for n in s_npcs}            # maps whose NPCs rAthena's own scripts run
    taken = collections.defaultdict(set)         # cells with an NPC or a portal on them
    for n in s_npcs + other_npcs(a.other_npcs):
        taken[n[0]].add((n[1], n[2]))
    for w in s_warps:
        taken[w[0]].add((w[1], w[2]))
    cells = {}

    def walkable(mp, x, y):
        if mp not in cells:
            cells[mp] = map_cells(grfs, mp) if grfs else None
        c = cells[mp]
        if not c:
            return True
        xs, ys, data = c
        return 0 <= x < xs and 0 <= y < ys and data[x + y * xs] in (0, 3)

    def free(mp, x, y, gap):
        return all(max(abs(x - tx), abs(y - ty)) > gap for tx, ty in taken[mp])

    def place(mp, x, y):
        """The spot itself when nothing stands within a cell of it, else the nearest walkable cell
        at least two cells from every other NPC (rings up to 8 cells out)."""
        if free(mp, x, y, 1):
            return x, y
        for rad in range(2, 9):
            ring = [(x + dx, y + dy) for dx in range(-rad, rad + 1) for dy in range(-rad, rad + 1)
                    if max(abs(dx), abs(dy)) == rad]
            ring.sort(key=lambda c: abs(c[0] - x) + abs(c[1] - y))
            for cx, cy in ring:
                if walkable(mp, cx, cy) and free(mp, cx, cy, 1):
                    return cx, cy
        return x, y

    npcs, placeholders, seen = [], [], set()
    for tag, r in nv['npc']:
        mp, name = str(r.get(1, '')).lower(), str(r.get(5, '') or '')
        x, y, sprite = r.get(7, 0), r.get(8, 0), r.get(4, 0)
        if mp not in loaded or mp in SKIP_MAPS or sprite in INVISIBLE or not name or (mp, x, y) in seen:
            continue
        seen.add((mp, x, y))
        if has_npc(mp, x, y, name):
            continue
        n = npc_name(names_en.get(name.strip(), name))
        role = npc_role(n)
        if role and (mp not in fillable or EVENT_MAP.search(mp)):
            role = None                           # rAthena's maps keep rAthena's services
        if mp in scripted and not role:
            # rAthena's scripts run this map: the client lists NPCs its quests show and hide on
            # cue, and an always-there copy with no logic only gets in the way
            report['NPCs left out (map already scripted by rAthena)'].append('%s %s' % (mp, n))
            continue
        nid = r.get(2, 0)
        if nid in positions:
            mp, x, y = positions[nid]
            report['NPCs at a position from npc_positions.txt'].append('%s %s' % (mp, n))
        else:
            nx, ny = place(mp, x, y)
            if (nx, ny) != (x, y):
                report['NPCs moved off another NPC'].append('%s %s %d,%d -> %d,%d' % (mp, n, x, y, nx, ny))
            x, y = nx, ny
        taken[mp].add((x, y))
        if (20000 <= sprite < 30000 or 1001 <= sprite < 4000) and sprite not in mobdb:
            # a monster's look for a monster the db doesn't have yet
            report['NPCs drawn as a townsperson (their monster sprite is not in the db)'].append('%s %s %d' % (mp, name, sprite))
            sprite = 'FALLBACK'
        if re.search(r'[\uac00-\ud7a3]', n):
            report['NPC names only in Korean (kRO-only NPCs)'].append('%s %s' % (mp, n))
        if role == 'tools':
            npcs.append('%s,%d,%d,4\tshop\t%s#ws%d\t%s,%s' % (mp, x, y, n, r.get(2, 0), '4_M_01' if sprite == 'FALLBACK' else sprite,
                                                            ','.join('%d:-1' % t for t in TOOLS)))
            report['working NPCs (tool shops)'].append('%s %s' % (mp, n))
            continue
        body = service_script(role, esc(n), mp, x, y) if role else None
        if body:
            report['working NPCs (%s)' % role].append('%s %s' % (mp, n))
        else:
            placeholders.append('%s,%d,%d,4\tscript\t%s#ws%d\t%s,{\n\tmes "[%s]";\n\tmes "Hello there, adventurer.";\n\tclose;\n}'
                                % (mp, x, y, n, r.get(2, 0), '4_M_01' if sprite == 'FALLBACK' else sprite, esc(n)))
            continue
        npcs.append('%s,%d,%d,4\tscript\t%s#ws%d\t%s,{\n%s}' % (mp, x, y, n, r.get(2, 0), '4_M_01' if sprite == 'FALLBACK' else sprite, body))

    # --- signboards with no NPC under them (iRO's S3 Season NPCs and the like)
    if a.signboards:
        before = {k: set(v) for k, v in taken.items()}   # signs only yield to real NPCs, not each other

        def free(mp, x, y, gap):
            return all(max(abs(x - tx), abs(y - ty)) > gap for tx, ty in before.get(mp, ()))
        sb = luadata.ordered_lines(luadata.run([a.signboards], 'latin-1').get('SignBoardList') or {})
        for i, r in enumerate(sb):
            if not isinstance(r, dict):
                continue
            mp, x, y, label = str(r.get(1, '')).lower(), r.get(2, 0), r.get(3, 0), str(r.get(7, '') or '')
            if mp not in loaded or not re.fullmatch(r'[A-Za-z][ -~]*', label) or re.search(r'\bonly\b|\.\d$', label):
                continue                           # notes ("Level 180 only.") aren't NPCs
            if not free(mp, x, y, 5) or has_npc(mp, x, y, label):
                continue                           # marks an NPC that is there
            n = npc_name(label)
            taken[mp].add((x, y))
            placeholders.append('%s,%d,%d,4\tscript\t%s#wsb%d\t4_M_01,{\n\tmes "[%s]";\n'
                        '\tmes "Hello there, adventurer.";\n\tclose;\n}' % (mp, x, y, n, i, esc(n)))
            report['NPCs placed at a signboard with nothing under it'].append('%s %s' % (mp, n))

    # --- write
    out = os.path.join(root, 'npc', 're', 'world_sync')
    os.makedirs(out, exist_ok=True)
    head = ('//===== rAthena Script =======================================\n'
            '//= %s\n//===== Description: =========================================\n'
            '//= GENERATED by tools/world_sync/generate.py from the official\n'
            '//= clients\' navigation tables. Do not edit by hand.\n'
            '//============================================================\n\n')
    files = {'spawns.txt': ('World sync: monster spawns', spawns),
             'warps.txt': ('World sync: warp portals', warps),
             'transports.txt': ('World sync: transport NPCs', transports),
             'npcs.txt': ('World sync: NPCs', npcs)}
    for fn, (title, lines) in files.items():
        with open(os.path.join(out, fn), 'w', encoding='cp949', errors='replace', newline='\n') as o:
            o.write(head % title + '\n'.join(lines) + '\n')
    with open(os.path.join(root, 'npc', 're', 'scripts_world_sync.conf'), 'w', newline='\n') as o:
        static = [fn for fn in ('rune_tablet.txt',) if os.path.exists(os.path.join(out, fn))]
        o.write('// World sync (generated by tools/world_sync/generate.py)\n' +
                ''.join('npc: npc/re/world_sync/%s\n' % fn for fn in list(files) + static))
    main_conf = os.path.join(root, 'npc', 're', 'scripts_main.conf')
    mc = open(main_conf).read()
    if 'scripts_world_sync.conf' not in mc:
        mc = mc.replace('import: npc/re/scripts_warps.conf\n',
                        'import: npc/re/scripts_warps.conf\nimport: npc/re/scripts_world_sync.conf\n')
        open(main_conf, 'w').write(mc)
    # map lists: one generated block each, rewritten every run (maps upstream ships drop out)
    idx = os.path.join(root, 'db', 'map_index.txt')
    official_idx = set(re.findall(r'^([a-z0-9_@.\-]+)', open(idx, errors='replace').read().split('\n' + MARK)[0], re.M))
    names = sorted(m for m in world if m not in maps and m not in official_idx)
    set_block(idx, ['%s\n' % m for m in names])
    set_block(os.path.join(root, 'conf', 'maps_athena.conf'), ['map: %s\n' % m for m in sorted(m for m in world if m not in maps)])
    # cells go to the renewal cache, never the shared db/map_cache.dat upstream rewrites
    have = cached(os.path.join(root, 'db', 'map_cache.dat'))
    add_to_cache(os.path.join(root, 'db', 're', 'map_cache.dat'), {m: c for m, c in new_maps.items() if m not in have})

    if a.entrances:
        with open(a.entrances, 'w', encoding='cp949', errors='replace', newline='\n') as o:
            o.write(head % 'World sync: entrances into the maps world sync fills (needs them in the client)'
                    + '\n'.join(sorted(set(entrances))) + '\n')
    if a.placeholders:
        with open(a.placeholders, 'w', encoding='cp949', errors='replace', newline='\n') as o:
            o.write(head % 'World sync: placeholder NPCs (sprite, name, spot; no logic yet)' + '\n'.join(placeholders) + '\n')
    stats = {'new maps': len(new_maps), 'spawns': len(spawns), 'warps': len(warps),
             'transports': len(transports), 'npcs': len(npcs),
             'placeholder npcs' + ('' if a.placeholders else ' (left out)'): len(placeholders),
             'entrances' + ('' if a.entrances else ' (left out)'): len(set(entrances))}
    for k, v in stats.items():
        print('%-12s %d' % (k, v))
    for k, v in report.items():
        print('%-45s %d' % (k, len(v)))
    if a.report:
        with open(a.report, 'w', encoding='utf-8') as r:
            json.dump({'stats': stats, 'report': report, 'new_maps': sorted(new_maps)}, r, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
