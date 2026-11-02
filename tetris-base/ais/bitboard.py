"""Fast board helpers shared by AIs.

Boards are lists of row bitmasks: row 0 at the top, bit c = column c.
"""


class Orientation:
    """One distinct rotation of a piece, precomputed for fast placement."""

    def __init__(self, matrix, offset):
        self.matrix = matrix
        # Column of the shape inside the C++ 4x4 box; C++ ties compare x - offset.
        self.offset = offset
        self.width = len(matrix[0])
        self.rows = [sum(1 << c for c, cell in enumerate(row) if cell) for row in matrix]
        # Lowest occupied row of each column, in piece-local coordinates.
        self.bottom = [max(r for r, row in enumerate(matrix) if row[c])
                       for c in range(self.width)]
        # Sum of the cells' row indices: 4 * y + landing_base = landing height x4.
        self.landing_base = sum(r for r, row in enumerate(matrix) for cell in row if cell)


# Each piece's rotations exactly as the C++ reference lists them (row bitmasks,
# bit c = column c), indexed like SHAPES. The order and offsets decide exact ties.
CPP_ROTATIONS = [
    [(0b1111,), (0b0100, 0b0100, 0b0100, 0b0100)],                    # I
    [(0b0011, 0b0011)],                                               # O
    [(0b0010, 0b0111), (0b0010, 0b0110, 0b0010),
     (0b0111, 0b0010), (0b0010, 0b0011, 0b0010)],                     # T
    [(0b0001, 0b0111), (0b0110, 0b0010, 0b0010),
     (0b0111, 0b0100), (0b0010, 0b0010, 0b0011)],                     # J
    [(0b0100, 0b0111), (0b0010, 0b0010, 0b0110),
     (0b0111, 0b0001), (0b0011, 0b0010, 0b0010)],                     # L
    [(0b0110, 0b0011), (0b0010, 0b0110, 0b0100)],                     # S
    [(0b0011, 0b0110), (0b0100, 0b0110, 0b0010)],                     # Z
]


def _orientation_from_bits(rows):
    combined = 0
    for row_bits in rows:
        combined |= row_bits
    offset = (combined & -combined).bit_length() - 1
    width = combined.bit_length() - offset
    matrix = [[(row_bits >> (offset + c)) & 1 for c in range(width)] for row_bits in rows]
    return Orientation(matrix, offset)


# ORIENTATIONS[kind] lists every distinct rotation of SHAPES[kind].
ORIENTATIONS = [[_orientation_from_bits(rows) for rows in piece] for piece in CPP_ROTATIONS]


def board_to_bits(board):
    return [sum(1 << c for c, v in enumerate(row) if v) for row in board]


def col_heights(bits, cols):
    rows = len(bits)
    heights = [0] * cols
    unresolved = (1 << cols) - 1
    for r, row_bits in enumerate(bits):
        new = row_bits & unresolved
        while new:
            low = new & -new
            heights[low.bit_length() - 1] = rows - r
            new ^= low
            unresolved &= ~low
        if not unresolved:
            break
    return heights


def drop_y(heights, rows, o, x):
    """Board row of the piece's top edge after a hard drop from above, or -1 if it
    would stick out above the board (a top-out)."""
    y = min(rows - heights[x + c] - o.bottom[c] - 1 for c in range(o.width))
    return y if y >= 0 else -1


def lock(bits, o, x, y, full_row_mask):
    """Return (new board bits, rows cleared) after locking o at (x, y)."""
    sim = bits[:]
    for r, row_bits in enumerate(o.rows):
        sim[y + r] |= row_bits << x
    remaining = [b for b in sim if b != full_row_mask]
    cleared = len(sim) - len(remaining)
    return [0] * cleared + remaining, cleared


def legal_placements(bits, heights, kind):
    """Yield (orientation, x, y, board_after, rows_cleared) for every hard drop of
    piece `kind` that does not top out, in the C++ reference's search order."""
    rows, cols = len(bits), len(heights)
    full_row_mask = (1 << cols) - 1
    for o in ORIENTATIONS[kind]:
        for x in range(cols - o.width + 1):
            y = drop_y(heights, rows, o, x)
            if y < 0:
                continue
            sim, cleared = lock(bits, o, x, y, full_row_mask)
            yield o, x, y, sim, cleared
