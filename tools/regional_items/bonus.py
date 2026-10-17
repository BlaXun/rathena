"""Turn the effect lines of an item description into rAthena item script.

The client describes every effect in prose (iRO in English, kRO in Korean).
This module knows the common phrasings: stats, damage modifiers, cast and
delay changes, skill damage and cooldowns, refine / grade / level conditions.
A line it can't read is returned as "unknown", so the generator can list it;
nothing is guessed.
"""
import re

STATS = {
    'str': 'bStr', 'agi': 'bAgi', 'vit': 'bVit', 'int': 'bInt', 'dex': 'bDex', 'luk': 'bLuk',
    'pow': 'bPow', 'sta': 'bSta', 'wis': 'bWis', 'spl': 'bSpl', 'con': 'bCon', 'crt': 'bCrt',
}
STAT_RE = '|'.join(STATS)

# flat / percent bonus of the short stat names the descriptions use
FLAT = {
    'atk': 'bBaseAtk', 'matk': 'bMatk', 'def': 'bDef', 'mdef': 'bMdef', 'hit': 'bHit',
    'flee': 'bFlee', 'cri': 'bCritical', 'crit': 'bCritical', 'critical': 'bCritical',
    'critical rate': 'bCritical', 'perfect dodge': 'bFlee2', 'p.atk': 'bPatk',
    's.matk': 'bSmatk', 'h.plus': 'bHplus', 'c.rate': 'bCrate', 'res': 'bRes',
    'mres': 'bMres', 'aspd': 'bAspd', 'mhp': 'bMaxHP', 'maxhp': 'bMaxHP', 'max hp': 'bMaxHP',
    'msp': 'bMaxSP', 'maxsp': 'bMaxSP', 'max sp': 'bMaxSP', 'map': 'bMaxAP', 'maxap': 'bMaxAP',
    'max ap': 'bMaxAP', 'hp': 'bMaxHP', 'sp': 'bMaxSP',
}
RATE = {
    'atk': 'bAtkRate', 'matk': 'bMatkRate', 'def': 'bDefRate', 'mdef': 'bMdefRate',
    'hit': 'bHitRate', 'flee': 'bFleeRate', 'aspd': 'bAspdRate', 'p.atk': 'bPAtkRate',
    's.matk': 'bSMatkRate', 'res': 'bResRate', 'mres': 'bMResRate', 'mhp': 'bMaxHPrate',
    'maxhp': 'bMaxHPrate', 'max hp': 'bMaxHPrate', 'msp': 'bMaxSPrate', 'maxsp': 'bMaxSPrate',
    'max sp': 'bMaxSPrate', 'hp': 'bMaxHPrate', 'sp': 'bMaxSPrate', 'map': 'bMaxAPrate',
    'maxap': 'bMaxAPrate', 'max ap': 'bMaxAPrate', 'cri': 'bCriticalRate',
    'critical': 'bCriticalRate', 'h.plus': 'bHPlusRate', 'c.rate': 'bCRateRate',
}
SHORT_RE = '|'.join(sorted((re.escape(k) for k in FLAT), key=len, reverse=True))

SIZES = {'all': 'Size_All', 'small': 'Size_Small', 'medium': 'Size_Medium', 'large': 'Size_Large'}
RACES = {
    'all': 'RC_All', 'formless': 'RC_Formless', 'undead': 'RC_Undead', 'brute': 'RC_Brute',
    'plant': 'RC_Plant', 'insect': 'RC_Insect', 'fish': 'RC_Fish', 'demon': 'RC_Demon',
    'demi-human': 'RC_DemiHuman', 'demihuman': 'RC_DemiHuman', 'demi human': 'RC_DemiHuman',
    'angel': 'RC_Angel', 'dragon': 'RC_Dragon', 'doram': 'RC_Player_Doram',
}
ELES = {
    'all': 'Ele_All', 'neutral': 'Ele_Neutral', 'water': 'Ele_Water', 'earth': 'Ele_Earth',
    'fire': 'Ele_Fire', 'wind': 'Ele_Wind', 'poison': 'Ele_Poison', 'holy': 'Ele_Holy',
    'shadow': 'Ele_Dark', 'dark': 'Ele_Dark', 'ghost': 'Ele_Ghost', 'undead': 'Ele_Undead',
}
KO_ELES = {'염': 'Ele_Ghost', '무': 'Ele_Neutral', '수': 'Ele_Water', '지': 'Ele_Earth', '화': 'Ele_Fire',
           '풍': 'Ele_Wind', '독': 'Ele_Poison', '성': 'Ele_Holy', '암': 'Ele_Dark',
           '념': 'Ele_Ghost', '불사': 'Ele_Undead'}
KO_RACES = {'무형': 'RC_Formless', '불사': 'RC_Undead', '동물': 'RC_Brute', '식물': 'RC_Plant',
            '곤충': 'RC_Insect', '어패': 'RC_Fish', '악마': 'RC_Demon', '인간': 'RC_DemiHuman',
            '천사': 'RC_Angel', '용': 'RC_Dragon', '도람': 'RC_Player_Doram'}
KO_SIZES = {'소형': 'Size_Small', '중형': 'Size_Medium', '대형': 'Size_Large'}

EQI_EN = {'weapon': 'EQI_HAND_R', 'armor': 'EQI_ARMOR', 'armour': 'EQI_ARMOR', 'shoes': 'EQI_SHOES',
          'footgear': 'EQI_SHOES', 'boots': 'EQI_SHOES', 'garment': 'EQI_GARMENT',
          'headgear': 'EQI_HEAD_TOP', 'helm': 'EQI_HEAD_TOP', 'shield': 'EQI_HAND_L'}
EQI_KO = {'무기': 'EQI_HAND_R', '갑옷': 'EQI_ARMOR', '신발': 'EQI_SHOES', '걸칠것': 'EQI_GARMENT',
          '투구': 'EQI_HEAD_TOP', '방패': 'EQI_HAND_L'}
UNBREAKABLE = {'Head_Top': 'bUnbreakableHelm', 'Head_Mid': 'bUnbreakableHelm',
               'Head_Low': 'bUnbreakableHelm', 'Armor': 'bUnbreakableArmor',
               'Garment': 'bUnbreakableGarment', 'Shoes': 'bUnbreakableShoes',
               'Left_Hand': 'bUnbreakableShield', 'Right_Hand': 'bUnbreakableWeapon',
               'Both_Hand': 'bUnbreakableWeapon'}

UNSUPPORTED = object()   # a condition this module can't express
SLOTS = 'weapon|armor|armour|shoes|garment|headgear|shield|helm|footgear|boots'


def num(s):
    v = float(s)
    return int(v) if v == int(v) else v


class Ctx:
    """What a translation needs to know beyond the line itself."""

    def __init__(self, skills, locations=(), in_combo=False, self_eqi=None, item_eqi=None):
        self.skills = skills            # lower-case skill name -> AegisName
        self.locations = list(locations)
        self.in_combo = in_combo
        self.self_eqi = self_eqi        # this item's slot, for combos
        self.item_eqi = item_eqi or {}  # lower-case item name -> slot (for "grade of <item>")

    def refine(self):
        return 'getequiprefinerycnt(%s)' % self.self_eqi if self.in_combo else 'getrefine()'

    def grade(self):
        return 'getenchantgrade(%s)' % self.self_eqi if self.in_combo else 'getenchantgrade()'


# ---------------------------------------------------------------- conditions

def _cmp(word):
    return '<=' if word in ('below', 'lower', 'less', 'under', '이하') else '>='


def parse_conditions(text, ctx):
    """Strip leading conditions. Returns (conds, mults, rest); conds may hold UNSUPPORTED."""
    conds, mults = [], []
    t = text.strip()
    while True:
        t0 = t
        low = t.lower()
        m = re.match(r'\[grade ([dcba])\]\s*', low)
        if m:
            conds.append('%s >= ENCHANTGRADE_%s' % (ctx.grade(), m.group(1).upper()))
            t = t[m.end():]
        m = re.match(r'\[([DCBA])등급\]\s*(?:이상인 경우,?\s*|이상일 경우,?\s*)?', t)
        if m:
            conds.append('%s >= ENCHANTGRADE_%s' % (ctx.grade(), m.group(1)))
            t = t[m.end():]
        low = t.lower()
        # grade of a slot or of a named item, optionally "and refined to +N"
        m = re.match(r'(?:when|if)\s+(?:the\s+)?(weapon|armor|armour|shoes|garment|headgear|shield|helm|footgear|boots)(?:\'s)?\s+(?:is\s+)?\[?grade(?:d)?\s+(?:is\s+)?(?:grade\s+)?([dcba])(?:\s+grade)?(?:\s+or\s+(?:higher|above|more|better))?', low) \
            or re.match(r'(?:when|if)\s+(?:the\s+)?grade\s+of\s+(?:the\s+)?(.+?)\s+is\s+(?:grade\s+)?([dcba])(?:\s+grade)?(?:\s+or\s+(?:higher|above|more|better))?', low)
        if m:
            what, grade = m.group(1), m.group(2)
            eqi = EQI_EN.get(what) or ctx.item_eqi.get(_name_key(what))
            if not eqi:
                conds.append(UNSUPPORTED)
            else:
                conds.append('getenchantgrade(%s) >= ENCHANTGRADE_%s' % (eqi, grade.upper()))
            t = t[m.end():]
            m2 = re.match(r'\s*,?\s*and\s+(?:is\s+)?(?:refined\s+(?:to\s+)?|refine\s+(?:level|rate)\s+is\s+)\+?(\d+)(?:\s+or\s+(?:higher|more|above))?', t.lower())
            if m2:
                conds.append(UNSUPPORTED if not eqi else 'getequiprefinerycnt(%s) >= %s' % (eqi, m2.group(1)))
                t = t[m2.end():]
        low = t.lower()
        m = re.match(r'(?:when|if)\s+(?:the\s+)?(weapon|armor|armour|shoes|garment|headgear|shield|helm|footgear|boots)\s+(?:is\s+)?(?:refined|refine\s+(?:level|rate)\s+is)\s*(?:to\s+|at\s+)?\+?(\d+)(?:\s+or\s+(?:higher|more|above))?', low)
        if m:
            conds.append('getequiprefinerycnt(%s) >= %s' % (EQI_EN[m.group(1)], m.group(2)))
            t = t[m.end():]
        low = t.lower()
        m = re.match(r'(?:when|if|at)\s+(?:the\s+)?(?:item\s+|it\s+|this\s+item\s+)?(?:is\s+)?(?:refined?|refine\s+(?:level|rate|value)(?:\s+of\s+(?:the\s+)?item)?\s+(?:is\s+)?|refinement\s+(?:level\s+)?(?:is\s+)?)\s*(?:to\s+|at\s+|of\s+)?\+?(\d+)(?:\s+or\s+(?:higher|more|above|over))?', low) \
            or re.match(r'(?:refine(?:d)?|refinement)\s+(?:level\s+)?\+?(\d+)\s+or\s+(?:higher|more|above)', low) \
            or re.match(r'\+(\d+)\s+refine(?:d)?(?:\s+or\s+(?:higher|more|above))?', low)
        if m:
            conds.append('%s >= %s' % (ctx.refine(), m.group(1)))
            t = t[m.end():]
        low = t.lower()
        m = re.match(r'(?:for\s+)?every\s+(\d+\s+)?(?:(%s)\s+)?(?:refine(?:ment)?|upgrade)s?\s*(?:levels?|rates?|lv)?(?:\s+(?:of|on)\s+(?:the\s+)?(%s))?' % (SLOTS, SLOTS), low)
        if m:
            n = int(m.group(1) or 1)
            slot = m.group(2) or m.group(3)
            base = 'getequiprefinerycnt(%s)' % EQI_EN[slot] if slot else ctx.refine()
            mults.append(base if n == 1 else '(%s/%d)' % (base, n))
            t = t[m.end():]
        low = t.lower()
        m = re.match(r'(?:when|if)\s+(?:your\s+|the\s+)?base\s+level\s+(?:is\s+)?(?:at\s+least\s+)?(\d+)(?:\s+or\s+(below|lower|less|under|higher|above|more))?', low)
        if m:
            conds.append('BaseLevel %s %s' % (_cmp(m.group(2) or 'higher'), m.group(1)))
            t = t[m.end():]
        low = t.lower()
        m = re.match(r'(?:for\s+)?every\s+(\d+)\s+base\s+levels?', low)
        if m:
            mults.append('(BaseLevel/%s)' % m.group(1))
            t = t[m.end():]
        low = t.lower()
        m = re.match(r'(?:for\s+)?every\s+(\d+)\s+(?:points?\s+of\s+)?(?:the\s+)?(?:sum\s+of\s+)?(?:base\s+|pure\s+)?(%s)(?:\s+(?:and|\+)\s+(?:base\s+|pure\s+)?(%s))?' % (STAT_RE, STAT_RE), low) \
            or re.match(r'(?:for\s+)?every\s+(\d+)\s+(?:points?\s+)?(?:sum\s+)?of\s+(?:base\s+|pure\s+)?(%s)\s+(?:and|\+)\s+(?:base\s+|pure\s+)?(%s)' % (STAT_RE, STAT_RE), low)
        if m:
            parts = ['readparam(%s)' % STATS[s] for s in m.groups()[1:] if s]
            mults.append('((%s)/%s)' % ('+'.join(parts), m.group(1)))
            t = t[m.end():]
        low = t.lower()
        m = re.match(r'(?:when|if)\s+(?:the\s+)?(?:base\s+|pure\s+)?(%s)\s+(?:is\s+)?(\d+)\s+or\s+(higher|more|above|below|lower|less)' % STAT_RE, low)
        if m:
            conds.append('readparam(%s) %s %s' % (STATS[m.group(1)], _cmp(m.group(3)), m.group(2)))
            t = t[m.end():]
        low = t.lower()
        m = re.match(r'(?:when|if)\s+(?:you\s+have\s+|the\s+user\s+has\s+)?(?:learned|mastered)\s+\[?(.+?)\]?\s+(?:skill\s+)?(?:at\s+)?(?:level\s+|lv\.?\s*)(\d+)(?:\s+or\s+(?:higher|above|more))?\s*[,:]', low)
        if m:
            sk = _skills(m.group(1), ctx)
            conds.append('getskilllv("%s") >= %s' % (sk[0], m.group(2)) if sk and len(sk) == 1 else UNSUPPORTED)
            t = t[m.end():]
        low = t.lower()
        m = re.match(r'(?:for\s+)?every\s+(?:(\d+)\s+)?(?:skill\s+)?levels?\s+of\s+(?:learned\s+)?\[?(.+?)\]?(?:\s+learned)?\s*[,:]', low)
        if m:
            sk = _skills(m.group(2), ctx)
            if sk and len(sk) == 1:
                n = int(m.group(1) or 1)
                mults.append('getskilllv("%s")' % sk[0] if n == 1 else '(getskilllv("%s")/%d)' % (sk[0], n))
            else:
                conds.append(UNSUPPORTED)
            t = t[m.end():]
        # Korean
        m = re.match(r'([DCBA])등급\s*이상(?:인 경우|일 경우|\s*시)?', t)
        if m:
            conds.append('%s >= ENCHANTGRADE_%s' % (ctx.grade(), m.group(1)))
            t = t[m.end():]
        m = re.match(r'(?:착용한\s*)?(무기|갑옷|신발|걸칠것|투구|방패)(?:의|가|이)?\s*([DCBA])등급\s*이상(?:인 경우|일 경우|\s*시)?', t)
        if m:
            conds.append('getenchantgrade(%s) >= ENCHANTGRADE_%s' % (EQI_KO[m.group(1)], m.group(2)))
            t = t[m.end():]
        m = re.match(r'(?:착용한\s*)?(무기|갑옷|신발|걸칠것|투구|방패)(?:의)?\s*제련도(?:가)?\s*(\d+)\s*이상(?:인 경우|일 경우|\s*시)?', t)
        if m:
            conds.append('getequiprefinerycnt(%s) >= %s' % (EQI_KO[m.group(1)], m.group(2)))
            t = t[m.end():]
        m = re.match(r'(?:착용한\s*)?(무기|갑옷|신발|걸칠것|투구|방패)(?:의)?\s*(?:제련도\s*(\d+)\s*당|(\d+)\s*제련\s*당|제련도\s*만큼)', t)
        if m:
            n = int(m.group(2) or m.group(3) or 1)
            base = 'getequiprefinerycnt(%s)' % EQI_KO[m.group(1)]
            mults.append(base if n == 1 else '(%s/%d)' % (base, n))
            t = t[m.end():]
        m = re.match(r'(\d+)\s*제련\s*(?:이상\s*)?(?:시|이상일 경우|이상인 경우|일 경우)', t)
        if m:
            conds.append('%s >= %s' % (ctx.refine(), m.group(1)))
            t = t[m.end():]
        m = re.match(r'(?:제련도\s*(\d+)\s*당|(\d+)\s*제련\s*당|제련도\s*만큼|제련\s*당)', t)
        if m:
            n = int(m.group(1) or m.group(2) or 1)
            mults.append(ctx.refine() if n == 1 else '(%s/%d)' % (ctx.refine(), n))
            t = t[m.end():]
        m = re.match(r'베이스\s*레벨(?:이)?\s*(\d+)\s*(이상|이하)(?:인 경우|일 경우|\s*시)?', t)
        if m:
            conds.append('BaseLevel %s %s' % (_cmp(m.group(2)), m.group(1)))
            t = t[m.end():]
        m = re.match(r'베이스\s*레벨\s*(\d+)\s*당', t)
        if m:
            mults.append('(BaseLevel/%s)' % m.group(1))
            t = t[m.end():]
        m = re.match(r'(?:순수\s*|기본\s*)?(%s)\s*(\d+)\s*당' % STAT_RE.upper(), t)
        if m:
            mults.append('(readparam(%s)/%s)' % (STATS[m.group(1).lower()], m.group(2)))
            t = t[m.end():]
        m = re.match(r'(?:순수\s*|기본\s*)?(%s)(?:이|가)?\s*(\d+)\s*(이상|이하)(?:인 경우|일 경우|\s*시)?' % STAT_RE.upper(), t)
        if m:
            conds.append('readparam(%s) %s %s' % (STATS[m.group(1).lower()], _cmp(m.group(3)), m.group(2)))
            t = t[m.end():]
        low = t.lower()
        m = re.match(r'(?:when|if)\s+(?:the\s+)?(.+?)\s+is\s+(?:refined\s+(?:to\s+)?(?:\+\s*)?|\+)(\d+)(?:\s+or\s+(?:higher|more|above))?(?:\s+refine(?:d)?)?', low)
        if m and t is t0:
            eqi = EQI_EN.get(m.group(1)) or ctx.item_eqi.get(_name_key(m.group(1)))
            conds.append('getequiprefinerycnt(%s) >= %s' % (eqi, m.group(2)) if eqi else UNSUPPORTED)
            t = t[m.end():]
        low = t.lower()
        m = re.match(r'(?:when|if)\s+(?:the\s+)?(.+?)(?:\'s\s+grade|\s+grade)?\s+is\s+\[?(?:grade\s+)?([dcba])(?:\s+grade)?\]?(?:\s+(?:grade\s+)?or\s+(?:higher|above|more|better))?(?=[\s,:])', low)
        if m and t is t0:
            eqi = EQI_EN.get(m.group(1)) or ctx.item_eqi.get(_name_key(m.group(1)))
            conds.append('getenchantgrade(%s) >= ENCHANTGRADE_%s' % (eqi, m.group(2).upper()) if eqi else UNSUPPORTED)
            t = t[m.end():]
            m2 = re.match(r'\s*,?\s*and\s+(?:is\s+)?(?:refined\s+(?:to\s+)?(?:\+\s*)?|\+)(\d+)(?:\s+or\s+(?:higher|more|above))?', t.lower())
            if m2:
                conds.append('getequiprefinerycnt(%s) >= %s' % (eqi, m2.group(1)) if eqi else UNSUPPORTED)
                t = t[m2.end():]
        # a condition we can't express: keep the effects out
        low = t.lower()
        m = re.match(r'(?:when|if|while)\s+[^,:]*?(?:,|:)\s*', low)
        ability = re.match(r'(?:when|upon|while)\s+(?:using|casting|receiving|dealing|performing|doing|equipped by|a physical|wearer|after using)', low)
        if m and t is t0 and not conds and not mults and not ability:
            conds.append(UNSUPPORTED)
            t = t[m.end():]
        t = re.sub(r'^[\s,:;]+', '', t)
        t = re.sub(r'^(?:and|then)\s+', '', t, flags=re.I)
        t = re.sub(r'^(?:grants the following effects?|the following effects?|gain the following|additionally)\s*[,:]?\s*', '', t, flags=re.I)
        if t == t0:
            break
    return conds, mults, t.strip()


def _name_key(s):
    s = re.sub(r'\^[0-9a-fA-F]{6}', '', s)
    s = re.sub(r'\[\d\]\s*$', '', s.strip())
    return re.sub(r'\s+', ' ', s).strip().lower()


# ---------------------------------------------------------------- effects

def _val(v, mults, scale=1):
    v = v * scale
    v = int(v) if float(v) == int(v) else v
    if not mults:
        return str(v)
    return '%s*%s' % (v, '*'.join(mults))


def _signed(sign, v):
    return -v if sign in ('-', 'reduce', 'decrease', '감소') else v


def _norm_en(s):
    s = s.strip().rstrip('.,;').strip()
    s = re.sub(r'\s+', ' ', s)
    low = s.lower()
    for a, b in ((r'\bincreases?\b|\bincreased\b', 'increase'), (r'\breduces?\b|\breduced\b|\bdecreases?\b|\bdecreased\b', 'reduce'),
                 (r'\bmagical\b', 'magic'), (r'physical ?/ ?magic|physical or magic|physical & magic', 'physical and magic'), (r'\bstate\b', 'stat'), (r'after skill delay', 'after cast delay'), (r'\bperfect hit\b', 'perfect hit'), (r'\benemies\b', 'enemy'), (r'\bmonsters\b', 'monster'),
                 (r'\bsizes\b', 'size'), (r'\braces\b', 'race'), (r'\bproperties\b|\belements?\b', 'property'),
                 (r'\bclasses\b', 'class'), (r'\bagainst\b|\btowards?\b|\bvs\.?', 'to'),
                 (r'\b(?:an |by )?additional(?:ly)?\b', ''), (r'\bfurther\b', ''), (r'\bextra\b', ''),
                 (r'\bdmg\b', 'damage'), (r'\bskill damage\b', 'damage'),
                 (r'after[- ]?cast[- ]?delay', 'after cast delay'), (r'\bacd\b', 'after cast delay'),
                 (r'\bvct\b', 'variable cast time'), (r'\bfct\b', 'fixed cast time'),
                 (r'casting time', 'cast time'), (r'\bseconds?\b|\bsecs?\.?', 'sec'),
                 (r'long[- ]?ranged?|ranged|\brange\b', 'long range'), (r'short[- ]range|melee', 'melee'),
                 (r'\bmax(?:imum)? ?hp\b', 'mhp'), (r'\bmax(?:imum)? ?sp\b', 'msp'),
                 (r'\bmax(?:imum)? ?ap\b', 'map'), (r'\btalent\b|\btraits?\b', 'trait'),
                 (r'\bstatus(?:es)?\b|\bstats?\b', 'stat'), (r'\bpatk\b|\bp\. atk\b', 'p.atk'),
                 (r'\bsmatk\b|\bs\. matk\b', 's.matk'), (r'\bcrate\b', 'c.rate'), (r'\bhplus\b', 'h.plus'),
                 (r'\bcritical damage\b', 'critical damage'), (r'\s+', ' ')):
        low = re.sub(a, b, low)
    low = re.sub(r'(physical|magic) damage given to', r'\1 damage to', low).strip()
    low = re.sub(r'\s+(?:is |are )?increase (?=by \d)', ' ', low)
    low = re.sub(r'^(?:(?:increase|gain|grant)s? )?(%s|atk|matk|flee|hit|def|mdef|cri|aspd|perfect dodge|p\.atk|s\.matk|mhp|msp) by (\d+)(%%?)$' % STAT_RE,
                 r'\1 + \2\3', low)
    low = re.sub(r'\s*\+\s*', ' + ', low)
    low = re.sub(r'\s*-\s*(?=\d)', ' - ', low)
    low = re.sub(r'(\d)\s*%', r'\1%', low)
    return low.strip(' .,')


def _target(t):
    """'all size enemy' -> ('Size', 'Size_All'); None if unknown."""
    t = re.sub(r'\s+(?:is\s+|are\s+)?increase$', '', t.strip())
    t = re.sub(r'\b(enemy|enemies|monster|monsters|target|targets|type|types|opponents?)\b', '', t)
    t = re.sub(r'\(except [^)]*\)|except players?( and doram)?', '', t)
    t = re.sub(r'\s+', ' ', t).strip(' ,')
    t = re.sub(r'^(?:of |with )', '', t)
    if re.fullmatch(r'(?:all|every) size|size all|all size(?:d)?|of all size|small, medium,? and large(?: size)?', t):
        return ('Size', 'Size_All')
    m = re.fullmatch(r'(small|medium|large)(?: size(?:d)?)?', t)
    if m:
        return ('Size', SIZES[m.group(1)])
    if re.fullmatch(r'(?:all|every) race|race all|all race(?:s)?|of all race|all|every', t):
        return ('Race', 'RC_All')
    m = re.fullmatch(r'(formless|undead|brute|plant|insect|fish|demon|demi-human|demihuman|demi human|angel|dragon|doram)(?: race)?', t)
    if m:
        return ('Race', RACES[m.group(1)])
    if re.fullmatch(r'(?:all|every) class|normal and boss|boss and normal|all class(?:es)?|normal and boss class|normal,? boss', t):
        return ('Class', 'Class_All')
    if re.fullmatch(r'(?:human and doram|doram and human) players?|players?', t):
        return ('Race', 'RC_Player_Human,RC_Player_Doram')
    if t in ('boss', 'boss class'):
        return ('Class', 'Class_Boss')
    if t in ('normal', 'normal class'):
        return ('Class', 'Class_Normal')
    if re.fullmatch(r'(?:all|every) property|all property|property all', t):
        return ('Ele', 'Ele_All')
    m = re.fullmatch(r'(neutral|water|earth|fire|wind|poison|holy|shadow|dark|ghost|undead)(?: property)?', t)
    if m:
        return ('Ele', ELES[m.group(1)])
    return None


def _loose_key(n):
    n = re.sub(r'^(?:use\s*)?\[|^the\s+', '', n.lower().strip())
    n = re.sub(r'[^a-z0-9]+', '', n)
    return re.sub(r'(?:s|es)$', '', n)


def _skill_loose(n, ctx):
    """'Musical Lesson' -> BA_MUSICALLESSON ('Music Lessons'); 'Backstab' -> 'Back Stab'."""
    if not hasattr(ctx, '_loose'):
        ctx._loose = {}
        for k, v in ctx.skills.items():
            if not v.startswith(('NPC_', 'ALL_')):
                ctx._loose.setdefault(_loose_key(k), v)
    k = _loose_key(n)
    if len(k) < 4:
        return None
    if k in ctx._loose:
        return ctx._loose[k]
    if len(k) >= 7:
        import difflib
        close = difflib.get_close_matches(k, list(ctx._loose), n=1, cutoff=0.86)
        if close and re.findall(r'\d+', close[0]) == re.findall(r'\d+', k):
            return ctx._loose[close[0]]
    return None


def _skills(names, ctx):
    whole = names.strip(' []"\'').strip()
    whole = re.sub(r'^(?:the|skill|skills)\s+', '', whole)
    whole = re.sub(r'\s+(?:skill|skills)$', '', whole)
    if whole.lower() in ctx.skills:
        return [ctx.skills[whole.lower()]]
    a = _skill_loose(whole, ctx) if not re.search(r',|\band\b|&|/', whole) else None
    if a:
        return [a]
    out = []
    for n in re.split(r'\s*(?:,|/|&|\band\b|\bor\b)\s*', names):
        n = n.strip(' []"\'').strip()
        n = re.sub(r'^(?:the|skill|skills)\s+', '', n)
        n = re.sub(r'\s+(?:skill|skills)$', '', n)
        if not n:
            continue
        a = ctx.skills.get(n.lower()) or _skill_loose(n, ctx)
        if not a:
            return None
        out.append(a)
    return out or None


def effect_en(s, mults, ctx):
    """One English effect clause -> list of script statements, or None."""
    low = _norm_en(s)
    if not low:
        return []
    V = lambda v, sc=1: _val(v, mults, sc)

    if low.startswith(('increase ', 'reduce ')) and re.fullmatch(r'(?:increase|reduce) (?:the )?(?:%s|all (?:basic |trait )?stat)\s*[+-]\s*\d+%%?' % SHORT_RE + '|(?:increase|reduce) (?:%s)\s*[+-]\s*\d+' % STAT_RE, low):
        return effect_en(re.sub(r'^(?:increase|reduce) (?:the )?', '', low), mults, ctx)
    m = re.fullmatch(r'indestructible(?: in battle)?|cannot be destroyed|unbreakable', low)
    if m:
        return ['bonus %s;' % UNBREAKABLE[l] for l in ctx.locations if l in UNBREAKABLE] or None
    m = re.fullmatch(r'((?:%s)(?:\s*(?:, and|,|and|/|&)\s*(?:%s))*)\s*([+-])\s*(\d+)' % (STAT_RE, STAT_RE), low)
    if m:
        v = _signed(m.group(2), int(m.group(3)))
        return ['bonus %s,%s;' % (STATS[x], V(v)) for x in re.findall(STAT_RE, m.group(1))]
    m = re.fullmatch(r'all (?:basic )?stat\s*([+-])\s*(\d+)', low)
    if m:
        return ['bonus bAllStats,%s;' % V(_signed(m.group(1), int(m.group(2))))]
    m = re.fullmatch(r'all trait stat\s*([+-])\s*(\d+)', low)
    if m:
        return ['bonus bAllTraitStats,%s;' % V(_signed(m.group(1), int(m.group(2))))]
    m = re.fullmatch(r'((?:%s)(?:\s*(?:, and|,|and|/|&)\s*(?:%s))*)\s*([+-])\s*(\d+)(%%)?' % (SHORT_RE, SHORT_RE), low)
    if m:
        v = _signed(m.group(2), int(m.group(3)))
        names = [x.strip() for x in re.split(r'\s*(?:,|\band\b|/|&)\s*', m.group(1)) if x.strip()]
        table = RATE if m.group(4) else FLAT
        if all(n in table for n in names):
            return ['bonus %s,%s;' % (table[n], V(v)) for n in names]
        return None
    m = re.fullmatch(r'(?:increase )?(?:attack speed|aspd)(?: increase)?\s*(?:\(\s*)?(?:after attack delay|delay after attack)\s*(?:-|reduce|by)?\s*(\d+)%\s*\)?', low) \
        or re.fullmatch(r'(?:increase )?(?:attack speed|aspd) (?:by )?(\d+)%', low) \
        or re.fullmatch(r'reduce (?:after attack delay|delay after attack) by (\d+)%', low)
    if m:
        return ['bonus bAspdRate,%s;' % V(int(m.group(1)))]

    # damage dealt
    m = re.fullmatch(r'(?:increase )?(?:magic damage (?:of|with) (.+?) property|(.+?) property magic damage|magic damage of (.+?) property|(.+?) magic damage)\s*(?:\+|by)\s*(\d+)%', low)
    if m:
        what = next(g for g in m.groups()[:4] if g)
        what = what.replace(' property', '').replace('all ', 'all ')
        consts = []
        for w in re.split(r'\s*(?:,|and|/)\s*', what):
            w = w.strip()
            if w in ('all', 'every'):
                consts.append('Ele_All')
            elif w in ELES:
                consts.append(ELES[w])
            else:
                return None
        return ['bonus2 bMagicAtkEle,%s,%s;' % (c, V(int(m.group(5)))) for c in consts]
    m = re.fullmatch(r'(?:increase )?(physical|magic|physical and magic|melee and long range physical|melee physical|long range physical) damage (?:to|on|for|vs|of|with|toward) (.+?)\s*(?:\+|by)\s*(\d+)%', low) \
        or re.fullmatch(r'(?:increase )?(physical|magic|physical and magic) damage (?:to|on) (.+?) (?:is )?increase (?:by )?(\d+)%', low) \
        or re.fullmatch(r'(physical|magic|physical and magic) damage (?:to|on) (.+?) increase (\d+)%', low)
    if m:
        kind, tgt, v = m.group(1), _target(m.group(2)), int(m.group(3))
        if not tgt:
            return None
        cat, consts = tgt
        out = []
        for const in consts.split(','):
            if 'physical' in kind:
                out.append('bonus2 bAdd%s,%s,%s;' % (cat, const, V(v)))
            if 'magic' in kind:
                out.append('bonus2 bMagicAdd%s,%s,%s;' % (cat, const, V(v)))
        if 'long range' in kind or 'melee' in kind:
            return None
        return out
    m = re.fullmatch(r'(?:increase )?(long range|melee|melee and long range|long range and melee) physical (?:attack )?damage\s*(?:is )?(?:increase )?(?:\+|by)\s*(\d+)%', low) \
        or re.fullmatch(r'(long range|melee) physical damage (?:is )?increase (?:by )?(\d+)%', low)
    if m:
        v = V(int(m.group(2)))
        out = []
        if 'melee' in m.group(1):
            out.append('bonus bShortAtkRate,%s;' % v)
        if 'long range' in m.group(1):
            out.append('bonus bLongAtkRate,%s;' % v)
        return out
    m = re.fullmatch(r'(?:increase )?critical (?:attack )?damage\s*(?:\+|by)\s*(\d+)%', low) \
        or re.fullmatch(r'critical damage (?:is )?increase (?:by )?(\d+)%', low)
    if m:
        return ['bonus bCritAtkRate,%s;' % V(int(m.group(1)))]
    m = re.fullmatch(r'(reduce |increase )?(?:the )?(?:after cast delay|global cooldown|global cool down|skill delay|skill usage delay|delay after skills?|skill post delay)(?: of all skills)?\s*(?:(-|\+)|by)?\s*(\d+)%', low)
    if m:
        sign = '-' if (m.group(1) or '').strip() == 'reduce' or m.group(2) == '-' else '+'
        return ['bonus bDelayrate,%s;' % V(_signed(sign, int(m.group(3))))]
    m = re.fullmatch(r'(reduce |increase )?variable cast time\s*(?:(-|\+)|by)?\s*(\d+)%', low)
    if m:
        sign = '-' if (m.group(1) or '').strip() == 'reduce' or m.group(2) == '-' else '+'
        return ['bonus bVariableCastrate,%s;' % V(_signed(sign, int(m.group(3))))]
    m = re.fullmatch(r'(reduce |increase )?fix(?:ed)? cast time\s*(?:(-|\+)|by)?\s*([\d.]+)\s*(sec|%)', low)
    if m:
        sign = '-' if (m.group(1) or '').strip() == 'reduce' or m.group(2) == '-' else '+'
        if m.group(4) == '%':
            return ['bonus bFixedCastrate,%s;' % V(_signed(sign, int(float(m.group(3)))))]
        return ['bonus bFixedCast,%s;' % V(_signed(sign, num(m.group(3))), 1000)]
    m = re.fullmatch(r'(?:increase )?(?:base and job )?exp(?:erience)?(?: gain(?:ed)?| obtained| earned)?(?: from (?:defeating |killing |hunting )?(?:the )?monster)?\s*(?:\+|by)\s*(\d+)%', low) \
        or re.fullmatch(r'(?:increase )?exp(?:erience)? gain(?:ed)? (?:when|by|from) (?:defeating|killing|hunting) monster (?:\+|by )?(\d+)%', low)
    if m:
        return ['bonus2 bExpAddRace,RC_All,%s;' % V(int(m.group(1)))]
    m = re.fullmatch(r'(?:increase )?(?:item )?drop rate(?: of items)?(?: from (?:the )?monster)?\s*(?:\+|by)\s*(\d+)%', low) \
        or re.fullmatch(r'(?:increase )?(?:the )?(?:item )?drop (?:chance|rate) (?:of|from) monster (?:\+|by )?(\d+)%', low)
    if m:
        return ['bonus2 bDropAddRace,RC_All,%s;' % V(int(m.group(1)))]
    low = re.sub(r'\s*\((?:permanent|does not stack|doesn\'t stack|same as|not stack)[^)]*\)', '', low).strip()
    if re.fullmatch(r'(?:increase |increased )?(?:the )?(?:movement|move|moving|walking|walk) speed(?: (?:increase|is increase|increased))?|increase (?:movement|move) speed', low):
        return ['bonus bSpeedRate,25;'] if not mults else None
    m = re.fullmatch(r'(?:increase )?(?:natural )?(hp|sp) (?:recovery|regen(?:eration)?)(?: rate)?\s*(?:\+|by)\s*(\d+)%?', low)
    if m:
        return ['bonus b%srecovRate,%s;' % (m.group(1).upper(), V(int(m.group(2))))]
    m = re.fullmatch(r'(?:increase )?(?:the )?(?:heal(?:ing)?|recovery) (?:power|effectiveness|effect|amount)(?: of (?:healing )?skills)?\s*(?:\+|by)\s*(\d+)%', low)
    if m:
        return ['bonus bHealPower,%s;' % V(int(m.group(1)))]

    m = re.fullmatch(r'(?:increase )?perfect hit\s*(?:\+|by)\s*(\d+)%', low)
    if m:
        return ['bonus bPerfectHitAddRate,%s;' % V(int(m.group(1)))]
    m = re.fullmatch(r'(?:increase )?exp(?:erience)? and (?:item )?drop rate(?: from monster)?\s*(?:\+|by)\s*(\d+)%', low)
    if m:
        return ['bonus2 bExpAddRace,RC_All,%s;' % V(int(m.group(1))), 'bonus2 bDropAddRace,RC_All,%s;' % V(int(m.group(1)))]
    m = re.fullmatch(r'(?:increase )?long range (?:physical )?(?:attack )?damage\s*(?:\+|by)\s*(\d+)%', low)
    if m:
        return ['bonus bLongAtkRate,%s;' % V(int(m.group(1)))]
    m = re.fullmatch(r'ignore (res|mres|res and mres) (?:of|to|on) (.+?)\s*(?:by )?(\d+)%', low)
    if m:
        tgt = _target(m.group(2))
        if not tgt or tgt[0] != 'Race':
            return None
        out = []
        if m.group(1) != 'mres':
            out.append('bonus2 bIgnoreResRaceRate,%s,%s;' % (tgt[1], V(int(m.group(3)))))
        if 'mres' in m.group(1):
            out.append('bonus2 bIgnoreMResRaceRate,%s,%s;' % (tgt[1], V(int(m.group(3)))))
        return out

    # damage taken
    m = re.fullmatch(r'reduce (?:(physical|magic|physical and magic) )?damage (?:taken |received )?(?:from|by) (.+?)\s*(?:by )?(\d+)%', low) \
        or re.fullmatch(r'(?:(physical|magic|physical and magic) )?damage (?:taken |received )?from (.+?)\s*-\s*(\d+)%', low)
    if m:
        tgt = _target(re.sub(r'\battacks?\b', '', m.group(2)))
        if not tgt:
            return None
        cat, consts = tgt
        return ['bonus2 bSub%s,%s,%s;' % (cat, c, V(int(m.group(3)))) for c in consts.split(',')]
    m = re.fullmatch(r'ignore (?:physical )?(def|mdef|def and mdef|physical and magic defense|physical defense|magic defense) (?:of|to|on) (.+?)\s*(?:by )?(\d+)%', low)
    if m:
        tgt = _target(m.group(2))
        if not tgt or tgt[0] not in ('Race', 'Class'):
            return None
        out = []
        kinds = m.group(1)
        if 'def' in kinds.replace('mdef', '') or 'physical' in kinds:
            out.append('bonus2 bIgnoreDef%sRate,%s,%s;' % (tgt[0], tgt[1], V(int(m.group(3)))))
        if 'mdef' in kinds or 'magic' in kinds:
            out.append('bonus2 bIgnoreMdef%sRate,%s,%s;' % (tgt[0], tgt[1], V(int(m.group(3)))))
        return out
    m = re.fullmatch(r'recovers? (\d+) (hp|sp) (?:each time|when|whenever) (?:you )?(?:defeat(?:ing)?|kill(?:ing)?) (?:a )?monster(?: with (physical|magic|physical or magic|physical and magic) attacks?)?', low)
    if m:
        v, w, k = V(int(m.group(1))), m.group(2).upper(), m.group(3) or 'physical'
        out = []
        if 'physical' in k:
            out.append('bonus b%sGainValue,%s;' % (w, v))
        if 'magic' in k:
            out.append('bonus bMagic%sGainValue,%s;' % (w, v))
        return out

    # skills
    low = re.sub(r'\s*\((?:buff|the buff|effect)[^)]*\)$', '', low)
    m = re.fullmatch(r'(?:enables?|enable to use|able to use|allows? (?:the )?use of|can use)(?: the)?(?: use of| to use| usage of| skill)? (?:level |lv\.? ?)(\d+) \[?(.+?)\]?', low) \
        or re.fullmatch(r'(?:enables?|enable to use|able to use|allows? (?:the )?use of|can use)(?: the)?(?: use of| to use| usage of| skill)? \[?(.+?)\]? (?:level |lv\.? ?)(\d+)()', low)
    if m:
        lv, name = (m.group(1), m.group(2)) if m.group(1).isdigit() else (m.group(2), m.group(1))
        sk = _skills(name, ctx)
        if sk and len(sk) == 1 and not mults:
            return ['skill "%s",%s;' % (sk[0], lv)]
        return None
    m = re.fullmatch(r'(?:increase )?(?:the )?(?:damage of )?(.+?)(?: damage)?\s*(?:\+|by)\s*(\d+)%', low) \
        or re.fullmatch(r'(.+?) damage (?:is )?increase (?:by )?(\d+)%', low) \
        or re.fullmatch(r'increase (?:the )?damage of (.+?) by (\d+)%', low) \
        or re.fullmatch(r'damage of (.+?) (?:is )?increase (?:by )?(\d+)%', low)
    if m and 'damage' in low:
        sk = _skills(re.sub(r'\s*damage$', '', m.group(1)), ctx)
        if sk:
            return ['bonus2 bSkillAtk,"%s",%s;' % (a, V(int(m.group(2)))) for a in sk]
    m = re.fullmatch(r'(?:reduce )?(?:the )?(?:cooldown|cool ?time|cool down|cooltime) of (.+?) (?:by |- ?)?([\d.]+) ?(?:sec|s)', low) \
        or re.fullmatch(r'(?:reduce )?(?:the )?(.+?)(?:\'s)? (?:cooldown|cool ?time|cool down|cooltime)\s*(?:-|by)?\s*([\d.]+) ?(?:sec|s)', low)
    if m:
        sk = _skills(m.group(1), ctx)
        if sk:
            return ['bonus2 bSkillCooldown,"%s",%s;' % (a, V(-num(m.group(2)), 1000)) for a in sk]
    m = re.fullmatch(r'(?:reduce )?(?:the )?(.+?) (?:sp cost|sp consumption)\s*(?:-|by)?\s*(\d+)(%)?', low)
    if m:
        sk = _skills(m.group(1), ctx)
        if sk:
            b = 'bSkillUseSPrate' if m.group(3) else 'bSkillUseSP'
            return ['bonus2 %s,"%s",%s;' % (b, a, V(int(m.group(2)))) for a in sk]
    m = re.fullmatch(r'(?:reduce )?(?:the )?(.+?) variable cast time\s*(?:-|by)?\s*([\d.]+) ?sec', low)
    if m:
        sk = _skills(m.group(1), ctx)
        if sk:
            return ['bonus2 bSkillVariableCast,"%s",%s;' % (a, V(-num(m.group(2)), 1000)) for a in sk]
    m = re.fullmatch(r'(?:when (?:dealing|performing|doing) (physical|magic|melee physical|long range physical|physical or magic|physical and magic) (?:attacks?|damage)[^,]*,? )?(?:has |there is |with )?(?:an? )?(?:certain|low|\d+(?:\.\d+)?%) chance (?:to |of )?(?:auto[- ]?cast(?:ing)?|cast(?:ing)?|trigger(?:ing)?) (?:level |lv\.? ?)(\d+) (.+?)(?: when (?:dealing|performing|doing) (physical|magic|melee physical|long range physical) (?:attacks?|damage))?', low)
    if m:
        rate = re.search(r'(\d+(?:\.\d+)?)% chance', low)
        sk = _skills(re.sub(r'\(.*\)$', '', m.group(3)).strip(), ctx)
        kind = m.group(1) or m.group(4) or 'physical'
        if rate and sk and len(sk) == 1 and not mults:
            r = int(round(float(rate.group(1)) * 10))
            if kind in ('physical', 'melee physical', 'long range physical'):
                return ['bonus3 bAutoSpell,"%s",%s,%s;' % (sk[0], m.group(2), r)]
            if kind == 'magic':
                return ['bonus5 bAutoSpell,"%s",%s,%s,BF_MAGIC,1;' % (sk[0], m.group(2), r)]
            return ['bonus5 bAutoSpell,"%s",%s,%s,BF_WEAPON|BF_MAGIC,1;' % (sk[0], m.group(2), r)]
    return None


def _norm_ko(s):
    s = s.strip().rstrip('.,;').strip()
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'\s*\((?:플레이어|player)[^)]*제외\)|\s*\(플레이어 제외\)', '', s)
    s = s.replace('추가 증가', '증가').replace('추가 감소', '감소').replace('추가로 ', '')
    s = re.sub(r'\s*\+\s*', ' + ', s)
    s = re.sub(r'(\d)\s*%', r'\1%', s)
    return s.strip(' .,')


def effect_ko(s, mults, ctx):
    t = _norm_ko(s)
    if not t:
        return []
    V = lambda v, sc=1: _val(v, mults, sc)
    low = t.lower()
    if re.fullmatch(r'파괴\s*불가', t):
        return ['bonus %s;' % UNBREAKABLE[l] for l in ctx.locations if l in UNBREAKABLE] or None
    m = re.fullmatch(r'모든 (?:기본 )?스테이터스 ([+-]) (\d+)', t)
    if m:
        return ['bonus bAllStats,%s;' % V(_signed(m.group(1), int(m.group(2))))]
    m = re.fullmatch(r'모든 특성 스테이터스 ([+-]) (\d+)', t)
    if m:
        return ['bonus bAllTraitStats,%s;' % V(_signed(m.group(1), int(m.group(2))))]
    # the short stat names are the same as iRO's
    r = effect_en(t, mults, ctx) if re.fullmatch(r'[A-Za-z.,/ ]+ [+-] \d+%?', t) else None
    if r:
        return r
    m = re.fullmatch(r'(?:공격 ?속도 증가\s*\(\s*)?공격 후 딜레이 (\d+)% 감소\s*\)?', t)
    if m:
        return ['bonus bAspdRate,%s;' % V(int(m.group(1)))]
    m = re.fullmatch(r'공격 ?속도 (\d+)% 증가', t)
    if m:
        return ['bonus bAspdRate,%s;' % V(int(m.group(1)))]
    m = re.fullmatch(r'모든 (크기|종족|속성|등급)(?:의)? (?:적에게 주는|대상|적 대상|적에게|몬스터에게 주는|몬스터 대상) (물리|마법|물리, 마법|물리 및 마법) 데미지 (\d+)% 증가', t) \
        or re.fullmatch(r'모든 (크기|종족|속성|등급)(?:의)? (?:적|몬스터)(?:에게| 대상) (물리|마법|물리, 마법) 데미지 (\d+)% 증가', t)
    if m:
        cat = {'크기': ('Size', 'Size_All'), '종족': ('Race', 'RC_All'), '속성': ('Ele', 'Ele_All'), '등급': ('Class', 'Class_All')}[m.group(1)]
        v = V(int(m.group(3)))
        out = []
        if '물리' in m.group(2):
            out.append('bonus2 bAdd%s,%s,%s;' % (cat[0], cat[1], v))
        if '마법' in m.group(2):
            out.append('bonus2 bMagicAdd%s,%s,%s;' % (cat[0], cat[1], v))
        return out
    m = re.fullmatch(r'(소형|중형|대형|무형|불사|동물|식물|곤충|어패|악마|인간|천사|용|도람)(?:형|족)? (?:몬스터|적)(?:에게 주는| 대상) (물리|마법) 데미지 (\d+)% 증가', t)
    if m:
        k = m.group(1)
        cat = ('Size', KO_SIZES[k]) if k in KO_SIZES else ('Race', KO_RACES[k])
        return ['bonus2 b%sAdd%s,%s,%s;' % ('' if m.group(2) == '물리' else 'Magic', cat[0], cat[1], V(int(m.group(3))))]
    m = re.fullmatch(r'(?:보스|일반)(?:, |와 |및 )(?:보스|일반) 몬스터(?:에게 주는| 대상) (물리|마법) 데미지 (\d+)% 증가', t)
    if m:
        return ['bonus2 b%sAddClass,Class_All,%s;' % ('' if m.group(1) == '물리' else 'Magic', V(int(m.group(2))))]
    m = re.fullmatch(r'모든 속성 마법 데미지 (\d+)% 증가', t)
    if m:
        return ['bonus2 bMagicAtkEle,Ele_All,%s;' % V(int(m.group(1)))]
    m = re.fullmatch(r'((?:무|수|지|화|풍|독|성|암|념|염|불사)(?:\s*,\s*(?:무|수|지|화|풍|독|성|암|념|염|불사))*)\s*속성 마법 데미지 (\d+)% 증가', t)
    if m:
        return ['bonus2 bMagicAtkEle,%s,%s;' % (KO_ELES[e], V(int(m.group(2)))) for e in re.split(r'\s*,\s*', m.group(1))]
    m = re.fullmatch(r'(원거리|근접|근거리)(?: 및 (?:원거리|근접))? 물리 (?:공격 )?데미지 (\d+)% 증가', t)
    if m:
        out = []
        if '근' in t.split('물리')[0]:
            out.append('bonus bShortAtkRate,%s;' % V(int(m.group(2))))
        if '원거리' in t.split('물리')[0]:
            out.append('bonus bLongAtkRate,%s;' % V(int(m.group(2))))
        return out
    m = re.fullmatch(r'크리티컬 데미지 (\d+)% 증가', t)
    if m:
        return ['bonus bCritAtkRate,%s;' % V(int(m.group(1)))]
    m = re.fullmatch(r'(?:스킬 )?(?:후 ?딜레이|스킬 후 딜레이|글로벌 쿨타임|글로벌 쿨 타임) (\d+)% (감소|증가)', t)
    if m:
        return ['bonus bDelayrate,%s;' % V(_signed(m.group(2), int(m.group(1))))]
    m = re.fullmatch(r'변동 ?캐스팅(?: 시간)? (\d+)% (감소|증가)', t)
    if m:
        return ['bonus bVariableCastrate,%s;' % V(_signed(m.group(2), int(m.group(1))))]
    m = re.fullmatch(r'고정 ?캐스팅(?: 시간)? ([\d.]+)(초|%) (감소|증가)', t)
    if m:
        if m.group(2) == '%':
            return ['bonus bFixedCastrate,%s;' % V(_signed(m.group(3), int(float(m.group(1)))))]
        return ['bonus bFixedCast,%s;' % V(_signed(m.group(3), num(m.group(1))), 1000)]
    m = re.fullmatch(r'(?:몬스터 처치 시 )?(?:획득 )?경험치(?: 획득량)? (\d+)% 증가', t)
    if m:
        return ['bonus2 bExpAddRace,RC_All,%s;' % V(int(m.group(1)))]
    m = re.fullmatch(r'(?:아이템 )?드롭(?:률| 확률) (\d+)% 증가', t)
    if m:
        return ['bonus2 bDropAddRace,RC_All,%s;' % V(int(m.group(1)))]
    if re.fullmatch(r'이동 ?속도(?:가)? 증가', t):
        return ['bonus bSpeedRate,25;'] if not mults else None
    m = re.fullmatch(r'(?:힐 |회복 )?(?:스킬 )?회복량 (\d+)% 증가', t)
    if m:
        return ['bonus bHealPower,%s;' % V(int(m.group(1)))]
    m = re.fullmatch(r'모든 (크기|종족|속성|등급)(?:의)? (?:적|몬스터)(?:에게|으로부터) 받는 (?:물리 |마법 |물리, 마법 )?데미지 (\d+)% 감소', t)
    if m:
        cat = {'크기': ('Size', 'Size_All'), '종족': ('Race', 'RC_All'), '속성': ('Ele', 'Ele_All'), '등급': ('Class', 'Class_All')}[m.group(1)]
        return ['bonus2 bSub%s,%s,%s;' % (cat[0], cat[1], V(int(m.group(2))))]
    m = re.fullmatch(r'(?:레벨 ?|Lv\.? ?)(\d+) (.+?)(?:을|를)? 사용 가능', t) or re.fullmatch(r'(.+?) (?:레벨 ?|Lv\.? ?)(\d+)()(?:을|를)? 사용 가능', t)
    if m:
        lv, name = (m.group(1), m.group(2)) if m.group(1).isdigit() else (m.group(2), m.group(1))
        sk = _skills(name.strip('[]'), ctx)
        if sk and len(sk) == 1 and not mults:
            return ['skill "%s",%s;' % (sk[0], lv)]
        return None
    m = re.fullmatch(r'(.+?) (?:스킬 )?데미지 (\d+)% 증가', t)
    if m:
        sk = _skills(m.group(1), ctx)
        if sk:
            return ['bonus2 bSkillAtk,"%s",%s;' % (a, V(int(m.group(2)))) for a in sk]
    m = re.fullmatch(r'(.+?)(?:의)? (?:재사용 대기 ?시간|쿨타임|쿨 타임) ([\d.]+)초 감소', t)
    if m:
        sk = _skills(m.group(1), ctx)
        if sk:
            return ['bonus2 bSkillCooldown,"%s",%s;' % (a, V(-num(m.group(2)), 1000)) for a in sk]
    m = re.fullmatch(r'(.+?)(?:의)? 변동 ?캐스팅 ([\d.]+)초 감소', t)
    if m:
        sk = _skills(m.group(1), ctx)
        if sk:
            return ['bonus2 bSkillVariableCast,"%s",%s;' % (a, V(-num(m.group(2)), 1000)) for a in sk]
    m = re.fullmatch(r'(.+?)(?:의)? (?:소모 )?SP(?: 소모량)? (\d+)(%)? 감소', t)
    if m:
        sk = _skills(m.group(1), ctx)
        if sk:
            b = 'bSkillUseSPrate' if m.group(3) else 'bSkillUseSP'
            return ['bonus2 %s,"%s",%s;' % (b, a, V(int(m.group(2)))) for a in sk]
    return None


def is_korean(s):
    return bool(re.search(r'[가-힣]', s))


def translate_clauses(text, mults, ctx):
    """A line of effects, split on commas. Returns (statements, ok)."""
    base = effect_ko if is_korean(text) else effect_en

    def eff(t, mults, ctx):
        r = base(t, mults, ctx)
        if r is None and not mults and base is effect_en:
            r = ability_en(t, ctx)
        if r is None and ' and ' in t:
            parts = [p for p in re.split(r'\s+and\s+', t) if p.strip()]
            got = [base(p, mults, ctx) or (None if mults else ability_en(p, ctx)) for p in parts]
            if len(parts) > 1 and all(g is not None for g in got):
                r = [x for g in got for x in g]
        return r
    whole = eff(text, mults, ctx)
    if whole is not None:
        return whole, True
    # split at commas / sentence ends, but only outside parentheses
    pieces, depth, cur = [], 0, ''
    for k, ch in enumerate(text):
        if ch in '([':
            depth += 1
        elif ch in ')]':
            depth = max(0, depth - 1)
        nxt = text[k + 1] if k + 1 < len(text) else ''
        if depth == 0 and (ch in ',;' or (ch == '.' and (nxt == '' or nxt == ' '))):
            pieces.append(cur)
            cur = ''
            continue
        cur += ch
    pieces.append(cur)
    pieces = [re.sub(r'^(?:and|also)\s+', '', p.strip(), flags=re.I) for p in pieces if p.strip()]
    if len(pieces) < 2:
        return [], False
    out = []
    i = 0
    while i < len(pieces):
        for j in range(len(pieces), i, -1):
            r = eff(', '.join(pieces[i:j]), mults, ctx)
            if r is not None:
                out.extend(r)
                i = j
                break
        else:
            return out, False
    return out, True


def translate_line(line, ctx, pending):
    """One description line. pending = (conds, mults) from a condition-only line
    above it. Returns (statements, new_pending, status) with status 'ok',
    'cond' (the line only set a condition), 'unknown' or 'skip'."""
    conds, mults, rest = parse_conditions(line, ctx)
    if not rest:
        if conds or mults:
            return [], (conds, mults), 'cond'
        return [], pending, 'skip'
    if conds or mults:
        allc, allm = list(pending[0]) + conds, list(pending[1]) + mults
    else:
        allc, allm = list(pending[0]), list(pending[1])
    if UNSUPPORTED in allc:
        return [], pending, 'unknown'
    stmts, ok = None, False
    if not allm and not is_korean(rest):
        jobs = re.split(r'(?:(?<=[.,])\s+|^)(?=when equipped by )', rest, flags=re.I)
        if len(jobs) > 1 or re.match(r'when equipped by ', rest, re.I):
            out = []
            for part in [p for p in jobs if p.strip()]:
                m = re.match(r'when equipped by (.+?)\s*[:,]\s*(.+?)[.,]?\s*$', part, re.I)
                cond = m and job_condition(m.group(1))
                inner = m and (ability_en(m.group(2), ctx) or translate_clauses(m.group(2), [], ctx)[0])
                if not (cond and inner):
                    out = None
                    break
                out.append('if %s {\n%s\n}' % (cond, '\n'.join('  ' + x for x in inner)))
            if out:
                stmts, ok = out, True
        if not ok:
            m = re.fullmatch(r'(.+?),? when equipped by ([A-Za-z &]+?)[.,]?(?:\s*,\s*(.+?) when equipped by ([A-Za-z &]+?)[.]?)?', rest, re.I)
            if m:
                out = []
                for eff, job in ((m.group(1), m.group(2)), (m.group(3), m.group(4))):
                    if not eff:
                        continue
                    cond = job_condition(job)
                    inner = ability_en(eff, ctx) or translate_clauses(eff, [], ctx)[0]
                    if not (cond and inner):
                        out = None
                        break
                    out.append('if %s {\n%s\n}' % (cond, '\n'.join('  ' + x for x in inner)))
                if out:
                    stmts, ok = out, True
        if not ok:
            a = ability_en(rest, ctx)
            if a:
                stmts, ok = a, True
    if not ok and not allm and is_korean(rest):
        a = ability_ko(rest, ctx)
        if a:
            stmts, ok = a, True
    if not ok:
        stmts, ok = translate_clauses(rest, allm, ctx)
    if not ok:
        return [], pending, 'unknown'
    if allc and stmts:
        body = '\n'.join('  ' + line for st in stmts for line in st.split('\n'))
        stmts = ['if (%s) {\n%s\n}' % (' && '.join(allc), body)]
    return stmts, pending, 'ok'


EFFECTISH = re.compile(r'[+%]|-\s*\d|\b(?:atk|matk|def|mdef|hit|flee|aspd|cri|str|agi|vit|int|dex|luk|pow|spl|con|sta|wis|crt|hp|sp|damage|cooldown|cast|delay|indestructible|movement speed|enables?|chance|autocast|auto-cast|recover|increase[sd]?|reduce[sd]?|ignore[sd]?)\b|데미지|증가|감소|파괴|사용 가능|회복', re.I)


def looks_like_effect(line):
    return bool(EFFECTISH.search(line))


# ---------------------------------------------------------------- abilities
# Effects that are more than a stat: timed buffs on skill use or on a chance,
# autocasts, enabled skills, per-job abilities.

JOB_CONSTS = [
    'NOVICE', 'SWORDMAN', 'MAGE', 'ARCHER', 'ACOLYTE', 'MERCHANT', 'THIEF', 'KNIGHT', 'PRIEST', 'WIZARD',
    'BLACKSMITH', 'HUNTER', 'ASSASSIN', 'CRUSADER', 'MONK', 'SAGE', 'ROGUE', 'ALCHEMIST', 'BARD', 'DANCER',
    'SUPER_NOVICE', 'GUNSLINGER', 'NINJA', 'LORD_KNIGHT', 'HIGH_PRIEST', 'HIGH_WIZARD', 'WHITESMITH', 'SNIPER',
    'ASSASSIN_CROSS', 'PALADIN', 'CHAMPION', 'PROFESSOR', 'STALKER', 'CREATOR', 'CLOWN', 'GYPSY', 'TAEKWON',
    'STAR_GLADIATOR', 'SOUL_LINKER', 'RUNE_KNIGHT', 'WARLOCK', 'RANGER', 'ARCH_BISHOP', 'MECHANIC',
    'GUILLOTINE_CROSS', 'ROYAL_GUARD', 'SORCERER', 'MINSTREL', 'WANDERER', 'SURA', 'GENETIC', 'SHADOW_CHASER',
    'KAGEROU', 'OBORO', 'REBELLION', 'SUMMONER', 'STAR_EMPEROR', 'SOUL_REAPER', 'DRAGON_KNIGHT', 'MEISTER',
    'SHADOW_CROSS', 'ARCH_MAGE', 'CARDINAL', 'WINDHAWK', 'IMPERIAL_GUARD', 'BIOLO', 'ABYSS_CHASER',
    'ELEMENTAL_MASTER', 'INQUISITOR', 'TROUBADOUR', 'TROUVERE', 'SKY_EMPEROR', 'SOUL_ASCETIC', 'SHINKIRO',
    'SHIRANUI', 'NIGHT_WATCH', 'HYPER_NOVICE', 'SPIRIT_HANDLER', 'DRUID', 'KARNOS', 'ALITEA']
JOB_VARIANTS = {'KNIGHT': ['2'], 'CRUSADER': ['2'], 'LORD_KNIGHT': ['2'], 'PALADIN': ['2'], 'STAR_GLADIATOR': ['2'],
                'RUNE_KNIGHT': ['_T', '2', '_T2', '_2ND'], 'ROYAL_GUARD': ['_T', '2', '_T2', '_2ND'],
                'RANGER': ['_T', '2', '_T2', '_2ND'], 'MECHANIC': ['_T', '2', '_T2', '_2ND'],
                'WARLOCK': ['_T', '_2ND'], 'ARCH_BISHOP': ['_T'], 'GUILLOTINE_CROSS': ['_T', '_2ND'],
                'SORCERER': ['_T', '_2ND'], 'MINSTREL': ['_T', '_2ND'], 'WANDERER': ['_T', '_2ND'],
                'SURA': ['_T', '_2ND'], 'GENETIC': ['_T', '_2ND'], 'SHADOW_CHASER': ['_T', '_2ND'],
                'STAR_EMPEROR': ['2'], 'DRAGON_KNIGHT': ['2'], 'MEISTER': ['2'], 'WINDHAWK': ['2'],
                'IMPERIAL_GUARD': ['2'], 'SKY_EMPEROR': ['2']}
JOB_ALIAS = {'wind hawk': 'WINDHAWK', 'archbishop': 'ARCH_BISHOP', 'geneticist': 'GENETIC',
             'troubadour & trouvere': 'TROUBADOUR|TROUVERE', 'troubadour&trouvere': 'TROUBADOUR|TROUVERE',
             'shinkiro & shiranui': 'SHINKIRO|SHIRANUI', 'kagerou & oboro': 'KAGEROU|OBORO',
             'minstrel & wanderer': 'MINSTREL|WANDERER', 'expanded super novice': 'SUPER_NOVICE_E'}


def job_condition(name):
    """'Imperial Guard' -> 'Class == JOB_IMPERIAL_GUARD || Class == JOB_IMPERIAL_GUARD2'."""
    n = re.sub(r'\b(?:class(?:es)?|jobs?)\b', '', name.lower()).strip(' .,:')
    keys = JOB_ALIAS.get(n) or re.sub(r'[^a-z]+', '_', n).strip('_').upper()
    out = []
    for k in keys.split('|'):
        if k not in JOB_CONSTS and k != 'SUPER_NOVICE_E':
            return None
        out += ['JOB_' + k] + ['JOB_' + k + v for v in JOB_VARIANTS.get(k, [])]
    return '(' + ' || '.join('Class == %s' % c for c in out) + ')'


def _flags(kind):
    kind = (kind or '').lower()
    bf = []
    if 'melee' in kind:
        bf.append('BF_SHORT')
    elif 'ranged' in kind or 'long' in kind:
        bf.append('BF_LONG')
    if 'magic' in kind and 'physical' in kind:
        bf.append('BF_WEAPON|BF_MAGIC')
    elif 'magic' in kind:
        bf.append('BF_MAGIC')
    else:
        bf.append('BF_WEAPON')
    return '|'.join(bf)


def _inner(text, ctx):
    """Effects inside a timed bonus, as one line of script for autobonus."""
    stmts, ok = translate_clauses(text, [], ctx)
    if not ok or not stmts:
        return None
    # a timed speed buff is the strong one (rAthena's +50%, as a Berserk
    # Potion); +25% is the permanent kind (Sleipnir, Increase AGI)
    stmts = [x.replace('bonus bSpeedRate,25;', 'bonus bSpeedRate,50;') for x in stmts]
    return ' '.join(stmts).replace('"', '\\"')


def _casts(text, ctx):
    """'Lv.1 Cart Tornado and Lv.1 Spore Explosion' -> [(aegis, lv)] or None."""
    one = re.sub(r'\(.*?\)', '', text).strip(' .[]')
    m = re.fullmatch(r'(?:level |lv\.? ?)(\d+) \[?(.+?)\]?', one, re.I) or re.fullmatch(r'\[?(.+?)\]? (?:level |lv\.? ?)(\d+)()', one, re.I)
    if m:
        lv, nm = (m.group(1), m.group(2)) if m.group(1).isdigit() else (m.group(2), m.group(1))
        if nm.lower().strip() in ctx.skills:
            return [(ctx.skills[nm.lower().strip()], lv)]
    out = []
    for part in re.split(r'\s*(?:,|\band\b|&)\s*', text):
        part = re.sub(r'\(.*?\)', '', part).strip(' .[]')
        part = re.sub(r'\s+(?:on (?:the )?(?:enemy|target|self|yourself))$', '', part)
        m = re.fullmatch(r'(?:level |lv\.? ?)(\d+) \[?(.+?)\]?', part, re.I) or \
            re.fullmatch(r'\[?(.+?)\]? (?:level |lv\.? ?)(\d+)()', part, re.I)
        if not m:
            return None
        lv, nm = (m.group(1), m.group(2)) if m.group(1).isdigit() else (m.group(2), m.group(1))
        sk = _skills(nm, ctx)
        if not sk or len(sk) != 1:
            return None
        out.append((sk[0], lv))
    return out or None


DEFAULT_CHANCE = 3   # percent, for "a certain chance" with no number


def ability_en(text, ctx):
    """A whole English line that is an ability, or None."""
    t = re.sub(r'\s+', ' ', text.strip()).rstrip('.,; ')
    t2 = re.sub(r'(?<![\w%])(?:a |an )?(?:(?:certain|random|low|small|slight) )?chance\b(?! \d)', 'a %d%% chance' % DEFAULT_CHANCE, t, flags=re.I)
    t2 = re.sub(r'\badds? (?:a )?(\d+% chance)', r'a \1', t2, flags=re.I)
    t2 = re.sub(r'^(?:a )?(\d+% chance)', r'\1', t2, flags=re.I)
    if t2 != t and not re.search(r'\d+(?:[.,]\d+)?\s*%\s*(?:of )?chance|chance\s*(?:of\s*)?\d', t, re.I):
        r = _ability_en(t2, ctx)
        if r:
            return r + ['// chance not stated in the description; %d%% assumed' % DEFAULT_CHANCE]
        return None
    return _ability_en(t, ctx)


def _ability_en(t, ctx):
    t = re.sub(r'^random (\d+% chance)', r'\1', t, flags=re.I)
    t = re.sub(r'\s*\((?:if (?:the )?user|if you have|status is removed|buff is|the buff|this effect|not applied)[^)]*\)', '', t, flags=re.I)
    low = t.lower()
    # timed bonus on skill use
    m = re.fullmatch(r'(?:when|upon|after) (?:using|casting) (?:the )?(?:skill )?\[?(.+?)\]?(?: skill)?[,:] (?:there\'?s? |has )?(?:a )?(?:(\d+)% chance to )?(?:gain |grants? |grant you )?(.+?) for (\d+) sec(?:onds?|s)?', low)
    if m and not re.search(r'auto[- ]?cast|\bcast\b|activate', m.group(3)):
        sk = _skills(m.group(1), ctx)
        inner = _inner(re.sub(r'\b(?:increase[sd]?|increasing)\s+(movement speed)', r'increase \1', m.group(3)), ctx)
        if sk and len(sk) == 1 and inner:
            rate = int(m.group(2)) * 10 if m.group(2) else 1000
            return ['autobonus3 "{ %s }",%d,%d,"%s";' % (inner, rate, int(m.group(4)) * 1000, sk[0])]
    # autocast on skill use
    m = re.fullmatch(r'(?:when|upon) (?:using|casting) (?:the )?(?:skill )?\[?(.+?)\]?(?: skill)?[,:] (?:there\'?s? |has |there is )?(?:a )?(?:chance (\d+)%|(\d+)% chance)? ?(?:to )?(?:auto[- ]?cast|cast|activate|trigger)s?(?: additional)? (.+)', low) \
        or re.fullmatch(r'(\d+)()% (?:chance to )?auto[- ]?casts? (.+?) when using (.+)', low)
    if m:
        if m.re.pattern.startswith('(\\d+)'):
            rate, dst, src = m.group(1), m.group(3), m.group(4)
        else:
            src, rate, dst = m.group(1), m.group(2) or m.group(3) or '100', m.group(4)
        s1 = _skills(src.strip('[] '), ctx)
        casts = _casts(dst, ctx)
        if s1 and len(s1) == 1 and casts:
            return ['bonus4 bAutoSpellOnSkill,"%s","%s",%s,%d;' % (s1[0], a, lv, int(rate) * 10) for a, lv in casts]
    m = re.fullmatch(r'(physical|magic(?:al)?|physical (?:and|or) magic(?:al)?|melee physical|ranged physical|long range physical) attacks? (?:have|has) (?:a )?(\d+)% chance to (.+)', low) or re.fullmatch(r'when (?:dealing|performing|doing) (physical|magic(?:al)?|physical (?:and|or) magic(?:al)?|melee physical|ranged physical) (?:attacks?|damages?),? (?:there\'?s? |has |there is )?(?:a )?(\d+)% chance to (.+)', low)
    if m:
        low = 'when dealing %s damage, %s%% chance to %s' % (m.group(1), m.group(2), m.group(3))
    m = re.fullmatch(r'(?:when )?(?:wearer )?receiv(?:ing|es?) (.+?) (?:attacks?|damages?),? (?:has |have |there is )?(?:a )?(\d+)% chance to (.+)', low) \
        or re.fullmatch(r'(\d+)()% chance to (.+?) when receiving (.+?) (?:attacks?|damage)', low)
    if m:
        if m.group(1).isdigit():
            low = 'when receiving %s damage, %s%% chance to %s' % (m.group(4), m.group(1), m.group(3))
        else:
            low = 'when receiving %s damage, %s%% chance to %s' % (m.group(1), m.group(2), m.group(3))
    m = re.fullmatch(r'(\d+)% chance to (.+?) when (?:dealing|performing|doing) (.+?) (?:attacks?|damage)', low)
    if m and not re.search(r'auto[- ]?cast|\bcast\b', m.group(2)):
        low = 'when dealing %s damage, %s%% chance to %s' % (m.group(3), m.group(1), m.group(2))
    # chance of a timed bonus on attack / when hit
    m = re.fullmatch(r'(?:when (?:dealing|performing|doing) (.+?) (?:attacks?|damage),? )?(?:there\'?s? |has |adds )?(?:a )?(\d+)% chance to (?:gain |grant |get |increase |decrease |reduce )?(.+?) for (\d+) sec(?:onds?|s)?(?: when (?:dealing|performing|doing) (.+?) (?:attacks?|damage))?', low)
    if m:
        inner = _inner(m.group(3), ctx)
        if inner:
            return ['autobonus "{ %s }",%d,%d,%s;' % (inner, int(m.group(2)) * 10, int(m.group(4)) * 1000, _flags(m.group(1) or m.group(5) or 'physical'))]
    m = re.fullmatch(r'when receiving (.+?) (?:attacks?|damage),? (?:there\'?s? |has )?(?:a )?(\d+)% chance to (?:gain |grant |get |increase |decrease |reduce )?(.+?) for (\d+) sec(?:onds?|s)?', low)
    if m:
        inner = _inner(m.group(3), ctx)
        if inner:
            return ['autobonus2 "{ %s }",%d,%d,%s;' % (inner, int(m.group(2)) * 10, int(m.group(4)) * 1000, _flags(m.group(1)))]
    # autocast on attack / when hit, several skills
    m = re.fullmatch(r'(?:there\'?s? |has |adds )?(?:a )?(\d+)% chance to (?:auto[- ]?cast|cast) (.+?) when (?:dealing|performing|doing) (.+?) (?:attacks?|damage)', low) \
        or re.fullmatch(r'when (?:dealing|performing|doing) (.+?) (?:attacks?|damage),? (?:there\'?s? |has )?(?:a )?(\d+)% chance to (?:auto[- ]?cast|cast) (.+)', low)
    if m:
        if m.group(1).isdigit():
            rate, dst, kind = m.group(1), m.group(2), m.group(3)
        else:
            kind, rate, dst = m.group(1), m.group(2), m.group(3)
        casts = _casts(dst, ctx)
        if casts:
            if _flags(kind) == 'BF_WEAPON':     # bonus3 targets self for self/support skills
                return ['bonus3 bAutoSpell,"%s",%s,%d;' % (a, lv, int(rate) * 10) for a, lv in casts]
            return ['bonus5 bAutoSpell,"%s",%s,%d,%s,1;' % (a, lv, int(rate) * 10, _flags(kind)) for a, lv in casts]
    m = re.fullmatch(r'when receiving (.+?) (?:attacks?|damage),? (?:there\'?s? |has )?(?:a )?(\d+)% chance to (?:auto[- ]?cast|cast) (.+?)(?: on (self|yourself))?', low)
    if m:
        casts = _casts(m.group(3), ctx)
        if casts:
            if _flags(m.group(1)) == 'BF_WEAPON' and not m.group(4):
                return ['bonus3 bAutoSpellWhenHit,"%s",%s,%d;' % (a, lv, int(m.group(2)) * 10) for a, lv in casts]
            target = 0 if m.group(4) else 1
            return ['bonus5 bAutoSpellWhenHit,"%s",%s,%d,%s,%d;' % (a, lv, int(m.group(2)) * 10, _flags(m.group(1)), target) for a, lv in casts]
    m = re.fullmatch(r'(?:enables?|allows?)(?: the)?(?: use of| to use)? (.+?) with (?:skill )?level equal to (?:the )?refine(?:ment)? level', low)
    if m:
        sk = _skills(m.group(1), ctx)
        if sk and len(sk) == 1:
            return ['if (getrefine()) skill "%s",getrefine();' % sk[0]]
    m = re.fullmatch(r'(?:enables?|allows?)(?: the)?(?: use of| to use)? (.+?), skill level is based on (.+?)(?: when equipped with .*)?', low)
    if m:
        s1, s2 = _skills(m.group(1), ctx), _skills(m.group(2), ctx)
        if s1 and s2 and len(s1) == 1 and len(s2) == 1:
            return ['if (getskilllv("%s")) skill "%s",getskilllv("%s");' % (s2[0], s1[0], s2[0])]
    # enabled skills, one or several
    m = re.fullmatch(r'(?:enables?|enable to use|able to use|allows?|can use)(?: the)?(?: use of| to use| usage of| use)? ?(.+?)(?: skill)?', low)
    if m:
        body = m.group(1)
        lvm = re.search(r'(?:level |lv\.? ?)(\d+)\s*$', body)
        parts = re.split(r'\s*(?:,|\band\b|&)\s*', body)
        if lvm and all(not re.search(r'\d', p) for p in parts[:-1]):
            parts = ['%s lv %s' % (re.sub(r'\s*(?:level |lv\.? ?)\d+$', '', p), lvm.group(1)) for p in parts]
        casts = _casts(', '.join(parts), ctx)
        if casts:
            return ['skill "%s",%s;' % (a, lv) for a, lv in casts]
    m = re.fullmatch(r'increases? (?:the )?(.+?) cool ?(?:down|time) by (\d+) sec(?:onds?|s)?', low)
    if m:
        sk = _skills(m.group(1), ctx)
        if sk:
            return ['bonus2 bSkillCooldown,"%s",%d;' % (a, int(m.group(2)) * 1000) for a in sk]
    return None


def ability_ko(text, ctx):
    t = _norm_ko(text)
    m = re.fullmatch(r'(.+?) (?:시전|사용) 시,? (?:(\d+)% 확률로 )?(.+?) (\d+)레벨 (?:추가 )?(?:자동 )?발동', t)
    if m:
        s1, s2 = _skills(m.group(1), ctx), _skills(m.group(3), ctx)
        if s1 and s2 and len(s1) == 1 and len(s2) == 1:
            return ['bonus4 bAutoSpellOnSkill,"%s","%s",%s,%d;' % (s1[0], s2[0], m.group(4), int(m.group(2) or 100) * 10)]
    m = re.fullmatch(r'(.+?) (?:시전|사용) 시,? (\d+)초(?:간| 동안) (.+)', t)
    if m:
        s1 = _skills(m.group(1), ctx)
        stmts, ok = translate_clauses(m.group(3), [], ctx)
        if s1 and len(s1) == 1 and ok and stmts:
            return ['autobonus3 "{ %s }",1000,%d,"%s";' % (' '.join(stmts).replace('"', '\\"'), int(m.group(2)) * 1000, s1[0])]
    m = re.fullmatch(r'(?:레벨 ?|Lv\.? ?)?(\d+)(?:레벨)? (.+?)(?:을|를)? 사용 가능', t)
    if m:
        sk = _skills(m.group(2), ctx)
        if sk and len(sk) == 1:
            return ['skill "%s",%s;' % (sk[0], m.group(1))]
    return None
