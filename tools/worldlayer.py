"""BD-1047: Python mirror of src/shared/WorldLayer.luau (docs/187 section D), so offline tools can read and write layers.

Same geometry (0-based cells, ix west to east, iz north to south, centred on 0, square cells) and the same text format:
  "WL1:<width>:<height>:<worldHalfWidth>:<body>", body = runs of equal cells, row by row; a zero run is the letters G..V (base-16
  digits of length - 1, G = 0), any other run is a hex digit 1..9 a..f plus g..v digits of length - 1 (none for length 1).
tools/verify_world_layer.py checks that Luau and Python read each other's text and write identical text.
"""
import math
import re

MAX_VALUE = 15
MAX_SIDE = 8192
MAX_CELLS = 16777216


def _digits(m, first):
    out = []
    while True:
        out.append(chr(first + m % 16))
        m //= 16
        if m == 0:
            break
    return ''.join(reversed(out))


class WorldLayer:
    def __init__(self, width, height, world_half_width):
        if int(width) != width or int(height) != height or width < 1 or height < 1:
            raise ValueError('width and height must be whole numbers of 1 or more')
        if width > MAX_SIDE or height > MAX_SIDE or width * height > MAX_CELLS:
            raise ValueError('layer is too large')
        if not (0 < world_half_width < math.inf):
            raise ValueError('world_half_width must be a positive number')
        self.width, self.height, self.world_half_width = int(width), int(height), float(world_half_width)
        self.cell_size = 2 * self.world_half_width / self.width
        self.cells = bytearray(self.width * self.height)

    # --- conversions
    def cell_of(self, x, z):
        half_depth = self.height * self.cell_size / 2
        return math.floor((x + self.world_half_width) / self.cell_size), math.floor((z + half_depth) / self.cell_size)

    def centre_of(self, ix, iz):
        half_depth = self.height * self.cell_size / 2
        return -self.world_half_width + (ix + 0.5) * self.cell_size, -half_depth + (iz + 0.5) * self.cell_size

    def contains(self, ix, iz):
        return 0 <= ix < self.width and 0 <= iz < self.height

    # --- reading and writing
    def at_cell(self, ix, iz):
        return self.cells[iz * self.width + ix] if self.contains(ix, iz) else 0

    def set_cell(self, ix, iz, value):
        if int(value) != value or not 0 <= value <= MAX_VALUE:
            raise ValueError('a value must be a whole number 0..15')
        if not self.contains(ix, iz):
            return False
        self.cells[iz * self.width + ix] = int(value)
        return True

    def at(self, x, z):
        return self.at_cell(*self.cell_of(x, z))

    def set(self, x, z, value):
        return self.set_cell(*self.cell_of(x, z), value)

    def fill(self, value):
        if int(value) != value or not 0 <= value <= MAX_VALUE:
            raise ValueError('a value must be a whole number 0..15')
        self.cells = bytearray([int(value)]) * (self.width * self.height)

    def count(self, value=None):
        if value is None:
            return len(self.cells) - self.cells.count(0)
        return self.cells.count(value)

    def neighbours(self, ix, iz, diagonals=False):
        steps = [(-1, 0), (1, 0), (0, -1), (0, 1)] + ([(-1, -1), (1, -1), (-1, 1), (1, 1)] if diagonals else [])
        return [{'ix': ix + dx, 'iz': iz + dz, 'value': self.at_cell(ix + dx, iz + dz)} for dx, dz in steps if self.contains(ix + dx, iz + dz)]

    def non_zero(self):
        """[(ix, iz, value)] for every cell that is not 0, row by row."""
        w = self.width
        return [(i % w, i // w, v) for i, v in enumerate(self.cells) if v]

    def rows(self):
        """rows[iz][ix] as lists of ints (the grid input of tools/layer_stats.py)."""
        w = self.width
        return [list(self.cells[r * w:(r + 1) * w]) for r in range(self.height)]

    # --- text
    def encode(self):
        parts = ['WL1:%d:%d:%s:' % (self.width, self.height, '%.9g' % self.world_half_width)]
        cells, total, i = self.cells, len(self.cells), 0
        while i < total:
            value = cells[i]
            j = i + 1
            while j < total and cells[j] == value:
                j += 1
            m = j - i - 1
            if value == 0:
                parts.append(_digits(m, 71))
            else:
                parts.append('%x' % value)
                if m:
                    parts.append(_digits(m, 103))
            i = j
        return ''.join(parts)

    def __eq__(self, other):
        return (isinstance(other, WorldLayer) and self.width == other.width and self.height == other.height
                and abs(self.world_half_width - other.world_half_width) < 1e-6 and self.cells == other.cells)


_HEADER = re.compile(r'^WL1:(\d+):(\d+):([\d.eE+\-]+):')


def decode(text):
    """Returns a WorldLayer; raises ValueError with a short reason when the text is not a valid layer."""
    clean = re.sub(r'\s', '', text)
    m = _HEADER.match(clean)
    if not m:
        raise ValueError('bad header (expected WL1:<width>:<height>:<worldHalfWidth>:)')
    try:
        width, height, half = int(m.group(1)), int(m.group(2)), float(m.group(3))
    except ValueError:
        raise ValueError('bad header numbers')
    if width < 1 or height < 1 or width > MAX_SIDE or height > MAX_SIDE or width * height > MAX_CELLS:
        raise ValueError('layer size out of range')
    if not (0 < half < math.inf):
        raise ValueError('worldHalfWidth must be positive')
    layer = WorldLayer(width, height, half)
    cells, total = layer.cells, width * height
    pos, i, n = 0, m.end(), len(clean)
    while i < n:
        c = ord(clean[i])
        if 71 <= c <= 86:
            value, first = 0, 71
        elif 48 <= c <= 57 or 97 <= c <= 102:
            value, first = (c - 48 if c <= 57 else c - 87), 103
            i += 1
        else:
            raise ValueError('unexpected character %r at %d' % (clean[i], i + 1))
        run = 0
        while i < n:
            d = ord(clean[i])
            if d < first or d > first + 15:
                break
            run = run * 16 + (d - first)
            i += 1
            if run >= total:
                break
        length = run + 1
        if pos + length > total:
            raise ValueError('more cells than width x height')
        if value:
            cells[pos:pos + length] = bytes([value]) * length
        pos += length
    if pos != total:
        raise ValueError('%d cells found, %d expected' % (pos, total))
    return layer
