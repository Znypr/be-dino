"""Tiny read-only reader for binary FBX files (what Blender's exporter writes): triangle count, vertex count, UV presence and the
bounding box of the exported geometry. Used by tools/verify_fx_textures.py to check the FX meshes (BD-430 / BD-431) against their
budgets without Blender. Handles FBX 7.x binary, 32-bit (< 7500) and 64-bit (>= 7500) node records, zlib-compressed arrays.

    python tools/fbx_stats.py assets/blender/fx/shock-dome.fbx
"""
import struct
import sys
import zlib
from pathlib import Path

MAGIC = b'Kaydara FBX Binary  \x00\x1a\x00'
_SCALAR = {'Y': ('<h', 2), 'C': ('<b', 1), 'I': ('<i', 4), 'F': ('<f', 4), 'D': ('<d', 8), 'L': ('<q', 8)}
_ARRAY = {'f': ('f', 4), 'd': ('d', 8), 'l': ('q', 8), 'i': ('i', 4), 'b': ('b', 1)}


def _props(data, pos, count, end):
    out = []
    for _ in range(count):
        t = chr(data[pos])
        pos += 1
        if t in _SCALAR:
            fmt, size = _SCALAR[t]
            out.append(struct.unpack_from(fmt, data, pos)[0])
            pos += size
        elif t in _ARRAY:
            code, size = _ARRAY[t]
            n, enc, clen = struct.unpack_from('<III', data, pos)
            pos += 12
            raw = data[pos:pos + clen]
            pos += clen
            if enc == 1:
                raw = zlib.decompress(raw)
            out.append(struct.unpack('<%d%s' % (n, code), raw[:n * size]))
        elif t in 'SR':
            n = struct.unpack_from('<I', data, pos)[0]
            pos += 4
            out.append(data[pos:pos + n])
            pos += n
        else:
            raise ValueError('unknown FBX property type %r' % t)
    return out


def _nodes(data, pos, end, wide):
    """Yield (name, props, children) for the node records between pos and end."""
    head = 25 if wide else 13
    out = []
    while pos + head <= end:
        if wide:
            node_end, nprops, plen, nlen = struct.unpack_from('<QQQB', data, pos)
        else:
            node_end, nprops, plen, nlen = struct.unpack_from('<IIIB', data, pos)
        if node_end == 0:
            break
        pos += head
        name = data[pos:pos + nlen].decode('ascii', 'replace')
        pos += nlen
        props = _props(data, pos, nprops, pos + plen)
        pos += plen
        children = _nodes(data, pos, node_end, wide) if pos < node_end else []
        out.append((name, props, children))
        pos = node_end
    return out


def _find(nodes, name):
    for n in nodes:
        if n[0] == name:
            yield n
        yield from _find(n[2], name)


def stats(path):
    data = Path(path).read_bytes()
    if not data.startswith(MAGIC):
        raise ValueError('not a binary FBX file: %s' % path)
    version = struct.unpack_from('<I', data, 23)[0]
    top = _nodes(data, 27, len(data), version >= 7500)
    geos = [n for n in _find(top, 'Geometry') if any(c[0] == 'Vertices' for c in n[2])]
    if not geos:
        raise ValueError('no Geometry node in %s' % path)
    tris = verts = 0
    mins, maxs, uv = [1e30] * 3, [-1e30] * 3, False
    for _, _, kids in geos:
        for name, props, sub in kids:
            if name == 'Vertices':
                v = props[0]
                verts += len(v) // 3
                for i in range(0, len(v), 3):
                    for k in range(3):
                        mins[k], maxs[k] = min(mins[k], v[i + k]), max(maxs[k], v[i + k])
            elif name == 'PolygonVertexIndex':
                idx = props[0]
                # a polygon ends at a negative index; a polygon with n corners is n - 2 triangles
                size = 0
                for i in idx:
                    size += 1
                    if i < 0:
                        tris += size - 2
                        size = 0
            elif name == 'LayerElementUV':
                uv = uv or any(c[0] == 'UV' and len(c[1][0]) > 0 for c in sub)
    return {'version': version, 'tris': tris, 'verts': verts, 'uv': uv, 'min': mins, 'max': maxs,
            'size': [maxs[k] - mins[k] for k in range(3)]}


if __name__ == '__main__':
    for p in sys.argv[1:]:
        print(p, stats(p))
