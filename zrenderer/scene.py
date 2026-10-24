"""Multi-panel figures and JSON scene files."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from . import mesh  # noqa: E402
from .render import render  # noqa: E402

PALETTE = [(0.25, 0.5, 0.88), (0.90, 0.55, 0.20), (0.35, 0.70, 0.40),
           (0.80, 0.30, 0.35), (0.55, 0.45, 0.80), (0.45, 0.45, 0.45)]


def parse_color(c, i=0):
    """Accept '#rrggbb', [r,g,b] in 0..1 or 0..255, or None (palette by index)."""
    if c is None:
        return PALETTE[i % len(PALETTE)]
    if isinstance(c, str):
        h = c.lstrip("#")
        if len(h) != 6:
            raise ValueError(f"bad color: {c}")
        return tuple(int(h[k:k + 2], 16) / 255 for k in (0, 2, 4))
    c = tuple(float(x) for x in c)
    return tuple(x / 255 for x in c) if max(c) > 1 else c


def save_image(path, img):
    plt.imsave(path, np.clip(img, 0, 1))


def figure(path, panels, width=560, height=560, dpi=100, title_size=13, background=(1, 1, 1)):
    """Save a row of rendered panels with titles.

    panels: list of dicts with keys ``parts`` ([(tris, color), ...]), and optional
    ``title``, ``elev``, ``azim``, ``bed``.
    """
    w_in, h_in = width / 560 * 5.2, height / 560 * 5.6
    f, axs = plt.subplots(1, len(panels), figsize=(w_in * len(panels), h_in))
    for ax, p in zip(np.atleast_1d(axs), panels):
        img = render(p["parts"], p.get("elev", 30), p.get("azim", -55), p.get("bed", False),
                     width, height, background)
        ax.imshow(img)
        ax.set_axis_off()
        if p.get("title"):
            ax.set_title(p["title"], fontsize=title_size)
    plt.tight_layout()
    f.savefig(path, dpi=dpi, facecolor=background)
    plt.close(f)


def run_scene(scene_path, out_dir=None, log=print):
    """Render every figure described in a JSON scene file. Returns the written paths.

    Relative model paths are resolved against the scene file; outputs against `out_dir`
    (default: the scene's ``output_dir`` or the scene file's directory).
    """
    with open(scene_path) as f:
        sc = json.load(f)
    base = os.path.dirname(os.path.abspath(scene_path))
    out_dir = out_dir or os.path.join(base, sc.get("output_dir", "."))
    os.makedirs(out_dir, exist_ok=True)
    defaults = sc.get("defaults", {})

    cache, models = {}, {}
    for i, (name, m) in enumerate(sc["models"].items()):
        m = {"file": m} if isinstance(m, str) else m
        fp = os.path.join(base, m["file"])
        if fp.lower().endswith(".json"):
            meshes = cache.setdefault(fp, mesh.load_json(fp))
            tris = meshes[m.get("key", name)]
        else:
            tris = cache.setdefault(fp, mesh.load(fp))
        models[name] = (mesh.apply(tris, m.get("transform")), parse_color(m.get("color"), i))

    written = []
    for fig in sc["figures"]:
        opts = {**defaults, **fig}
        panels = []
        for p in fig["panels"]:
            p = {**{k: opts[k] for k in ("elev", "azim", "bed") if k in opts}, **p}
            parts = []
            for ref in p["parts"]:
                ref = {"model": ref} if isinstance(ref, str) else ref
                tris, col = models[ref["model"]]
                tris = mesh.apply(tris, ref.get("transform"))
                parts.append((tris, parse_color(ref["color"]) if "color" in ref else col))
            panels.append({**p, "parts": parts})
        out = os.path.join(out_dir, fig["output"])
        figure(out, panels, opts.get("width", 560), opts.get("height", 560),
               opts.get("dpi", 100), opts.get("title_size", 13),
               parse_color(opts.get("background", "#ffffff")))
        log(out)
        written.append(out)
    return written
