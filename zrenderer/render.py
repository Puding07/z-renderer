"""Tiny z-buffer rasterizer: triangles in, shaded RGB image out (numpy only)."""
import numpy as np

BED_COLOR = (0.82, 0.82, 0.82)


def camera(elev, azim):
    """Orthonormal camera basis (right, up, fwd) for elevation/azimuth in degrees.

    `fwd` points from the model towards the camera.
    """
    e, a = np.radians(elev), np.radians(azim)
    fwd = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    right = np.array([-np.sin(a), np.cos(a), 0.0])
    up = np.cross(fwd, right)
    return right, up, fwd


def bed_quad(points, margin=0.35, color=BED_COLOR):
    """A flat print bed under the lowest point of `points`, as a (tris, color) part."""
    z0 = points[:, 2].min()
    lo, hi = points.min(0), points.max(0)
    m = (hi - lo).max() * margin
    x0, x1, y0, y1 = lo[0] - m, hi[0] + m, lo[1] - m, hi[1] + m
    q = np.array([[[x0, y0, z0], [x1, y0, z0], [x1, y1, z0]],
                  [[x0, y0, z0], [x1, y1, z0], [x0, y1, z0]]])
    return q, color


def render(parts, elev=30.0, azim=-55.0, bed=False, width=560, height=560,
           background=(1.0, 1.0, 1.0), fill=0.9):
    """Render `parts` = [(tris (N,3,3) array, rgb color), ...] to an (H,W,3) float image.

    elev/azim are in degrees (azim measured from +X towards +Y, elev from the XY plane).
    `bed=True` adds a grey plate under the model. `fill` is the fraction of the image
    the model's bounding box occupies.
    """
    W, H = int(width), int(height)
    right, up, fwd = camera(elev, azim)
    parts = [(np.asarray(t, float).reshape(-1, 3, 3), c) for t, c in parts]
    if bed:
        parts = parts + [bed_quad(np.concatenate([t.reshape(-1, 3) for t, _ in parts]))]
    allp = np.concatenate([t.reshape(-1, 3) for t, _ in parts])
    P2 = np.stack([allp @ right, allp @ up], 1)
    lo, hi = P2.min(0), P2.max(0)
    ext = np.maximum(hi - lo, 1e-9)
    s = fill * min(W / ext[0], H / ext[1])
    off = (np.array([W, H]) - s * (hi - lo)) / 2 - s * lo

    zb = np.full((H, W), -np.inf)
    img = np.empty((H, W, 3))
    img[:] = background
    # key light fixed relative to the camera, mixed with a world-space top light
    L = np.array([0.3, -0.5, 0.8]); L = L / np.linalg.norm(L)
    Lw = 0.6 * (L[0] * right + L[1] * up + L[2] * fwd) + 0.8 * np.array([0.2, -0.3, 1.0])
    Lw /= np.linalg.norm(Lw)

    for tr, col in parts:
        if not len(tr):
            continue
        col = np.asarray(col, float)
        n = np.cross(tr[:, 1] - tr[:, 0], tr[:, 2] - tr[:, 0])
        n /= np.linalg.norm(n, axis=1)[:, None] + 1e-12
        n *= np.sign(n @ fwd)[:, None]                      # two-sided: face the camera
        shade = 0.30 + 0.70 * np.clip(n @ Lw, 0, 1) + 0.15 * np.clip(n @ fwd, 0, 1)
        sx = tr @ right * s + off[0]
        sy = H - (tr @ up * s + off[1])
        sz = tr @ fwd
        for i in range(len(tr)):
            xs, ys, zs = sx[i], sy[i], sz[i]
            xa, xb = int(max(xs.min(), 0)), int(min(np.ceil(xs.max()), W - 1))
            ya, yb = int(max(ys.min(), 0)), int(min(np.ceil(ys.max()), H - 1))
            if xa > xb or ya > yb:
                continue
            d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
            if abs(d) < 1e-9:
                continue
            X, Y = np.meshgrid(np.arange(xa, xb + 1) + 0.5, np.arange(ya, yb + 1) + 0.5)
            w0 = ((ys[1] - ys[2]) * (X - xs[2]) + (xs[2] - xs[1]) * (Y - ys[2])) / d
            w1 = ((ys[2] - ys[0]) * (X - xs[2]) + (xs[0] - xs[2]) * (Y - ys[2])) / d
            w2 = 1 - w0 - w1
            ins = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            z = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
            sub = zb[ya:yb + 1, xa:xb + 1]
            upd = ins & (z > sub)
            sub[upd] = z[upd]
            img[ya:yb + 1, xa:xb + 1][upd] = np.clip(col * min(shade[i], 1.15), 0, 1)
    return img
