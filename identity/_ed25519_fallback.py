
"""Pure-Python Ed25519 fallback (RFC 8032 compliant). Used when PyNaCl unavailable."""

import hashlib, os

P = 2**255 - 19
EDWARDS_D = ((-121665) * pow(121666, P-2, P)) % P
I = pow(2, (P-1)//4, P)  # sqrt(-1) mod P

class _FE:
    __slots__ = ("v",)
    def __init__(self, v): self.v = v % P
    def __add__(self, o): return _FE((self.v + o.v) % P)
    def __sub__(self, o): return _FE((self.v - o.v) % P)
    def __neg__(self): return _FE((-self.v) % P)
    def __mul__(self, o): return _FE((self.v * o.v) % P)
    def __truediv__(self, o): return self * o.inv()
    def __eq__(self, o): return self.v == o.v
    def inv(self): return _FE(pow(self.v, P-2, P))
    def sqrt(self):
        y = pow(self.v, (P+3)//8, P)
        if (y*y) % P == self.v: return _FE(y)
        y = (y * I) % P
        if (y*y) % P == self.v: return _FE(y)
        return None
    def bytes32(self): return self.v.to_bytes(32, "little")
    @staticmethod
    def from32(b): return _FE(int.from_bytes(b, "little"))

class _Pt:
    __slots__ = ("x","y","z","t")
    def __init__(self, x, y, z, t):
        self.x=x; self.y=y; self.z=z; self.t=t
    def __eq__(self, o):
        return self.x*o.z == o.x*self.z and self.y*o.z == o.y*self.z
    def __add__(self, o):
        A = (self.y - self.x)*(o.y - o.x)
        B = (self.y + self.x)*(o.y + o.x)
        C = _FE(2*EDWARDS_D) * self.t * o.t
        D = _FE(2) * self.z * o.z
        E = B - A; F = D - C; G = D + C; H = B + A
        return _Pt(E*F, G*H, F*G, E*H)
    def double(self):
        A = self.x*self.x; B = self.y*self.y; C = _FE(2)*self.z*self.z
        H = A + B; E = H - (self.x+self.y)*(self.x+self.y)
        G = A - B; F = C + G
        return _Pt(E*F, G*H, F*G, E*H)
    def __mul__(self, k):
        r = _Pt(_FE(0), _FE(1), _FE(1), _FE(0))
        s = self
        while k > 0:
            if k & 1: r = r + s
            s = s.double()
            k >>= 1
        return r
    def affine(self):
        zi = self.z.inv()
        return (self.x*zi, self.y*zi)
    def enc(self):
        x, y = self.affine()
        b = bytearray(y.bytes32())
        if x.v & 1: b[31] |= 0x80
        return bytes(b)
    @staticmethod
    def dec(b):
        if len(b) != 32: return None
        yb = bytearray(b); s = yb[31] >> 7; yb[31] &= 0x7f
        y = _FE.from32(bytes(yb))
        y2 = y*y; u = y2 - _FE(1); v = _FE(EDWARDS_D)*y2 + _FE(1)
        x2 = u / v; x = x2.sqrt()
        if x is None: return None
        if (x.v & 1) != s: x = -x
        return _Pt(x, y, _FE(1), x*y)

# Correct base point (RFC 8032)
_By = _FE(46316835694926478169428394003475163141307993866256225615783033603165251855960)
_Bx = _FE(15112221349535400772501151409588531511454012693041857206046113283949847762202)
B = _Pt(_Bx, _By, _FE(1), _Bx*_By)

L = 2**252 + 27742317777372353535851937790883648493  # group order

def _h(b): return hashlib.sha512(b).digest()

def _clamp(a):
    a = bytearray(a); a[0] &= 0xf8; a[31] = (a[31] & 0x7f) | 0x40; return bytes(a)

class Ed25519Fallback:
    __slots__ = ("seed", "a", "A", "pub")
    def __init__(self, seed):
        self.seed = seed
        h = _h(seed)
        self.a = int.from_bytes(_clamp(h[:32]), "little")
        self.A = B * self.a
        self.pub = self.A.enc()
    @property
    def public_bytes(self): return self.pub
    def sign(self, msg):
        h = _h(self.seed)
        r = int.from_bytes(_h(h[32:64] + msg), "little") % L
        R = B * r
        k = int.from_bytes(_h(R.enc() + self.pub + msg), "little")
        S = (r + k * self.a) % L
        return R.enc() + S.to_bytes(32, "little")
    def verify(self, msg, sig):
        if len(sig) != 64: return False
        R = _Pt.dec(sig[:32]); S = int.from_bytes(sig[32:], "little")
        if S >= L: return False
        A = _Pt.dec(self.pub)
        if R is None or A is None: return False
        k = int.from_bytes(_h(sig[:32] + self.pub + msg), "little")
        return (B * S) == (R + (A * k))

class X25519Fallback:
    @staticmethod
    def scalar_mult(scalar, point):
        if len(scalar) != 32 or len(point) != 32: raise ValueError("need 32 bytes")
        s = bytearray(scalar); s[0] &= 0xf8; s[31] &= 0x7f; s[31] |= 0x40
        k = int.from_bytes(bytes(s), "little")
        u = int.from_bytes(point, "little") % P
        x1, x2, z2, x3, z3 = u, 1, 0, u, 1
        swap = 0
        for t in range(255, -1, -1):
            kt = (k >> t) & 1; swap ^= kt
            if swap: x2, x3 = x3, x2; z2, z3 = z3, z2
            swap = kt
            A = (x2 + z2) % P; B = (x2 - z2) % P
            AA = (A*A) % P; BB = (B*B) % P; E = (AA - BB) % P
            C = (x3 + z3) % P; D = (x3 - z3) % P
            DA = (D*A) % P; CB = (C*B) % P
            x3 = ((DA + CB)**2) % P
            z3 = (u * ((DA - CB)**2)) % P
            x2 = (AA * BB) % P
            z2 = (E * ((AA + ((121665 * E) % P)) % P)) % P
        if swap: x2, x3 = x3, x2; z2, z3 = z3, z2
        zi = pow(z2, P-2, P)
        return ((x2 * zi) % P).to_bytes(32, "little")
    @staticmethod
    def keypair():
        priv = os.urandom(32)
        pub = X25519Fallback.scalar_mult(priv, (9).to_bytes(32, "little"))
        return priv, pub
    @staticmethod
    def shared_secret(priv, pub):
        return X25519Fallback.scalar_mult(priv, pub)
