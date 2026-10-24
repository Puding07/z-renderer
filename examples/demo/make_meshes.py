"""Generate the demo meshes (a threaded-looking rod and a hex nut) as STL files."""
import os

import numpy as np


def prism(n, r_out, r_in, z0, z1, phase=0.0):
    """n-sided tube between radii r_in and r_out (r_in=0: solid prism)."""
    a = np.linspace(0, 2 * np.pi, n + 1)[:-1] + phase
    o = np.stack([r_out * np.cos(a), r_out * np.sin(a)], 1)
    i = np.stack([r_in * np.cos(a), r_in * np.sin(a)], 1)
    T = []
    for k in range(n):
        j = (k + 1) % n
        lo_o, hi_o = [*o[k], z0], [*o[k], z1]
        lo_o2, hi_o2 = [*o[j], z0], [*o[j], z1]
        T += [[lo_o, lo_o2, hi_o2], [lo_o, hi_o2, hi_o]]                 # outer wall
        if r_in > 0:
            lo_i, hi_i, lo_i2, hi_i2 = [*i[k], z0], [*i[k], z1], [*i[j], z0], [*i[j], z1]
            T += [[lo_i, hi_i2, lo_i2], [lo_i, hi_i, hi_i2]]             # inner wall
            for z in (z0, z1):                                           # annular caps
                T += [[[*o[k], z], [*o[j], z], [*i[j], z]], [[*o[k], z], [*i[j], z], [*i[k], z]]]
        else:
            for z in (z0, z1):
                T += [[[0, 0, z], [*o[k], z], [*o[j], z]]]
    return np.array(T, float)


def write_stl(path, tris):
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    n /= np.linalg.norm(n, axis=1)[:, None] + 1e-12
    rec = np.zeros(len(tris), np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")]))
    rec["n"], rec["v"] = n, tris
    with open(path, "wb") as f:
        f.write(b"zrenderer demo".ljust(80, b"\0"))
        f.write(np.uint32(len(tris)).tobytes())
        f.write(rec.tobytes())


here = os.path.dirname(os.path.abspath(__file__))
# rod: head + shaft made of stacked rings, so it reads like a thread
rod = [prism(6, 8, 0, 0, 5)] + [prism(48, 4.0 if k % 2 else 3.6, 0, 5 + k, 6 + k) for k in range(25)]
write_stl(os.path.join(here, "rod.stl"), np.concatenate(rod))
write_stl(os.path.join(here, "nut.stl"), prism(6, 7, 4.1, 0, 6, np.pi / 6))
print("rod.stl, nut.stl")
