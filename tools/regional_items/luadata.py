"""Read the data tables of RO client Lua files (itemInfo.lub, skillinfolist.lub).

The client ships them as Lua 5.1 bytecode. They only build tables of constants,
so this runs the handful of opcodes that do that and skips the rest (function
calls are not executed). Plain-text .lua tables are not supported: compile them
with luac 5.1 first.
"""
import struct


class _Proto:
    pass


class _Closure:
    def __init__(self, proto):
        self.proto = proto


def _load(data, enc):
    if data[:4] != b'\x1bLua' or data[4] != 0x51:
        raise ValueError('not Lua 5.1 bytecode')
    pos = [12]

    def rd(fmt):
        v = struct.unpack_from(fmt, data, pos[0])
        pos[0] += struct.calcsize(fmt)
        return v[0]

    def rstr():
        n = rd('<I')
        if n == 0:
            return None
        s = data[pos[0]:pos[0] + n - 1]
        pos[0] += n
        return s.decode(enc, 'replace')

    def func():
        f = _Proto()
        rstr(); rd('<i'); rd('<i')
        f.nups = rd('B'); rd('B'); rd('B'); rd('B')
        n = rd('<i')
        f.code = struct.unpack_from('<%dI' % n, data, pos[0])
        pos[0] += 4 * n
        f.k = []
        for _ in range(rd('<i')):
            t = rd('B')
            if t == 0:
                f.k.append(None)
            elif t == 1:
                f.k.append(bool(rd('B')))
            elif t == 3:
                v = rd('<d')
                f.k.append(int(v) if v == int(v) else v)
            elif t == 4:
                f.k.append(rstr())
            else:
                raise ValueError('constant type %d' % t)
        f.p = [func() for _ in range(rd('<i'))]
        n = rd('<i')                    # line info
        pos[0] += 4 * n
        for _ in range(rd('<i')):       # locals
            rstr(); rd('<i'); rd('<i')
        for _ in range(rd('<i')):       # upvalue names
            rstr()
        return f

    return func()


def _run(f, G):
    R = [None] * 256
    top = 0
    code = f.code
    pc = 0

    def RK(x):
        return f.k[x - 256] if x >= 256 else R[x]

    while pc < len(code):
        i = code[pc]
        pc += 1
        op = i & 0x3f
        A = (i >> 6) & 0xff
        C = (i >> 14) & 0x1ff
        B = (i >> 23) & 0x1ff
        Bx = i >> 14
        if op == 0:                     # MOVE
            R[A] = R[B]
        elif op == 1:                   # LOADK
            R[A] = f.k[Bx]
        elif op == 2:                   # LOADBOOL
            R[A] = bool(B)
            if C:
                pc += 1
        elif op == 3:                   # LOADNIL
            for j in range(A, B + 1):
                R[j] = None
        elif op == 5:                   # GETGLOBAL
            R[A] = G.get(f.k[Bx])
        elif op == 6:                   # GETTABLE
            t = R[B]
            R[A] = t.get(RK(C)) if isinstance(t, dict) else None
        elif op == 7:                   # SETGLOBAL
            G[f.k[Bx]] = R[A]
        elif op == 9:                   # SETTABLE
            if isinstance(R[A], dict):
                k = RK(B)
                if k is not None:
                    R[A][k] = RK(C)
        elif op == 10:                  # NEWTABLE
            R[A] = {}
        elif op in (12, 13, 14, 15, 16, 17):
            a, b = RK(B), RK(C)
            try:
                R[A] = [a + b, a - b, a * b, a / b, a % b, a ** b][op - 12]
            except Exception:
                R[A] = None
        elif op == 18:                  # UNM
            R[A] = -R[B] if isinstance(R[B], (int, float)) else None
        elif op == 21:                  # CONCAT
            try:
                R[A] = ''.join(str(R[j]) for j in range(B, C + 1))
            except Exception:
                R[A] = None
        elif op == 22:                  # JMP
            pc += Bx - 131071
        elif op == 28:                  # CALL: not executed
            for j in range(max(C - 1, 1)):
                R[A + j] = None
            top = A
        elif op == 30:                  # RETURN
            return
        elif op == 34:                  # SETLIST
            n, c = B, C
            if c == 0:
                c = code[pc]
                pc += 1
            if n == 0:
                n = top - A - 1
            for j in range(1, n + 1):
                R[A][(c - 1) * 50 + j] = R[A + j]
        elif op == 36:                  # CLOSURE
            R[A] = _Closure(f.p[Bx])
            pc += f.p[Bx].nups


def run(paths, enc, G=None):
    """Run each bytecode file in turn; returns the globals they set."""
    G = {} if G is None else G
    for p in paths:
        with open(p, 'rb') as fh:
            _run(_load(fh.read(), enc), G)
    return G


def ordered_lines(t):
    """A Lua array table ({[1]=..., [2]=...}) as a Python list."""
    if isinstance(t, list):
        return t
    if not isinstance(t, dict):
        return []
    return [t[k] for k in sorted(k for k in t if isinstance(k, int))]
