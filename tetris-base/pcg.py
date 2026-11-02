"""Python port of pcg32_k2_fast from the PCG library, plus the C++ reference's
3-bit rejection sampler, so a seed gives exactly the same pieces as the C++ code."""

MASK32 = 0xFFFFFFFF
MASK64 = 0xFFFFFFFFFFFFFFFF


def _unxorshift32(x, bits, shift):
    """Invert x ^= x >> shift on a bits-wide value (pcg_extras::unxorshift)."""
    if 2 * shift >= bits:
        return x ^ (x >> shift)
    lowmask1 = (1 << (bits - shift * 2)) - 1
    highmask1 = ~lowmask1 & MASK32
    top1 = x
    bottom1 = x & lowmask1
    top1 ^= top1 >> shift
    top1 &= highmask1
    x = top1 | bottom1
    lowmask2 = (1 << (bits - shift)) - 1
    bottom2 = x & lowmask2
    bottom2 = _unxorshift32(bottom2, bits - shift, shift)
    bottom2 &= lowmask1
    return top1 | bottom2


class Pcg32K2Fast:
    """pcg32_k2_fast: a 64-bit single-stream LCG with XSH RS output, extended by a
    2-entry table of 32-bit RXS M XS generators that is XORed into each output."""

    MULT64 = 6364136223846793005
    INC64 = 1442695040888963407
    # Constants of the 32-bit table generators (oneseq_rxs_m_xs_32_32).
    MULT32 = 747796405
    INC32 = 2891336453
    MCG_MULT32 = 277803737
    MCG_UNMULT32 = 2897767785

    def __init__(self, seed):
        self.state = self._bump((seed + self.INC64) & MASK64)
        # selfinit(): fill the table from the base generator.
        lhs = self._base()
        rhs = self._base()
        xdiff = (lhs - rhs) & MASK32
        self.data = [self._base() ^ xdiff for _ in range(2)]

    def _bump(self, state):
        return (state * self.MULT64 + self.INC64) & MASK64

    def _base(self):
        # XSH RS output of the state *before* advancing (output_previous).
        old = self.state
        self.state = self._bump(old)
        rshift = (old >> 61) & 7
        old ^= old >> 22
        return (old >> (22 + rshift)) & MASK32

    @classmethod
    def _rxs_m_xs(cls, x):
        rshift = (x >> 28) & 15
        x ^= x >> (4 + rshift)
        x = (x * cls.MCG_MULT32) & MASK32
        return x ^ (x >> 22)

    @classmethod
    def _un_rxs_m_xs(cls, x):
        x = _unxorshift32(x, 32, 22)
        x = (x * cls.MCG_UNMULT32) & MASK32
        rshift = (x >> 28) & 15
        return _unxorshift32(x, 32, 4 + rshift)

    def _external_step(self, i):
        """Step table entry i by one on its own stream; True when it wraps to 0."""
        state = self._un_rxs_m_xs(self.data[i])
        state = (state * self.MULT32 + self.INC32 + (i + 1) * 2) & MASK32
        self.data[i] = self._rxs_m_xs(state)
        return self.data[i] == 0

    def _advance_table(self):
        carry = False
        for i in range(len(self.data)):
            if carry:
                carry = self._external_step(i)
            carry2 = self._external_step(i)
            carry = carry or carry2

    def __call__(self):
        """Next 32-bit output."""
        index = self.state & 1
        # The table advances every 2^32 outputs, when the low state bits are zero.
        if self.state & MASK32 == 0:
            self._advance_table()
        rhs = self.data[index]
        return self._base() ^ rhs


def seed_from_int(seed):
    """Same seed conversion as the C++ reference (int -> uint32 -> uint64)."""
    return seed & MASK32


class PieceTypeRng:
    """Uniform piece types in [0, 6] via 3-bit rejection sampling over the
    generator's bit stream (a value of 7 is rejected); leftover bits carry over.

    Types use the C++ order I, J, L, O, S, T, Z.
    """

    def __init__(self, rng):
        self.rng = rng
        self.buf = 0
        self.bits_left = 0

    def next(self):
        while True:
            if self.bits_left < 3:
                self.buf |= self.rng() << self.bits_left
                self.bits_left += 32
            val = self.buf & 7
            self.buf >>= 3
            self.bits_left -= 3
            if val < 7:
                return val
