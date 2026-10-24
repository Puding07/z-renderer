"""Command line: `zrender model.stl -o out.png` or `zrender --scene scene.json`."""
import argparse
import sys

from . import mesh, scene
from .render import render


def parse_view(s):
    try:
        elev, azim = (float(x) for x in s.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"view must be ELEV,AZIM (got {s!r})")
    return elev, azim


def main(argv=None):
    ap = argparse.ArgumentParser(prog="zrender", description="Render STL/OBJ/JSON meshes to PNG "
                                 "with a tiny numpy z-buffer rasterizer.")
    ap.add_argument("models", nargs="*", help="mesh files (.stl, .obj, .json); rendered together")
    ap.add_argument("--scene", help="JSON scene file describing several figures")
    ap.add_argument("-o", "--output", help="output PNG (models mode) or directory (scene mode)")
    ap.add_argument("--view", type=parse_view, action="append", metavar="ELEV,AZIM",
                    help="camera view in degrees; repeat for side-by-side panels (default 30,-55)")
    ap.add_argument("--title", action="append", help="panel title; repeat once per --view")
    ap.add_argument("--color", action="append", help="color per model: #rrggbb or r,g,b")
    ap.add_argument("--bed", action="store_true", help="draw a print bed under the model")
    ap.add_argument("--rotate", action="append", metavar="AX,AY,AZ,DEG",
                    help="rotate all models (about the origin) before rendering; repeatable")
    ap.add_argument("--size", default="560x560", metavar="WxH", help="panel size in pixels")
    ap.add_argument("--background", default="#ffffff")
    a = ap.parse_args(argv)

    if a.scene:
        scene.run_scene(a.scene, a.output)
        return 0
    if not a.models:
        ap.error("give mesh files or --scene")

    w, h = (int(x) for x in a.size.lower().split("x"))
    bg = scene.parse_color(a.background)
    colors = a.color or []
    parts = []
    for i, path in enumerate(a.models):
        tris = mesh.load(path)
        for r in a.rotate or []:
            *axis, deg = (float(x) for x in r.split(","))
            tris = mesh.rotate(tris, axis, deg)
        c = colors[i] if i < len(colors) else None
        if c and not c.startswith("#"):
            c = [float(x) for x in c.split(",")]
        parts.append((tris, scene.parse_color(c, i)))

    views = a.view or [(30.0, -55.0)]
    titles = a.title or []
    out = a.output or "render.png"
    if len(views) == 1 and not titles:
        scene.save_image(out, render(parts, *views[0], a.bed, w, h, bg))
    else:
        panels = [dict(parts=parts, elev=e, azim=az, bed=a.bed,
                       title=titles[i] if i < len(titles) else None)
                  for i, (e, az) in enumerate(views)]
        scene.figure(out, panels, w, h, background=bg)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
