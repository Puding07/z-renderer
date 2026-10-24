"""Tessellate a STEP / FCStd / BREP file with FreeCAD into a zrenderer mesh JSON.

    python3 tools/freecad_export.py model.step mesh.json [--tol 0.02] [--names screw,nut]

Each solid becomes one named mesh (solid0, solid1, ... unless --names is given), so
the JSON can be referenced from a scene file with "key". Needs FreeCAD's Python
modules; common install locations are added to sys.path automatically.
"""
import argparse
import json
import sys

for p in ("/usr/lib/freecad/lib", "/usr/lib/freecad-python3/lib", "/usr/local/lib/freecad/lib",
          "/Applications/FreeCAD.app/Contents/Resources/lib"):
    if p not in sys.path:
        sys.path.append(p)

# FreeCAD parses sys.argv on import (and may quit on our file arguments), so hide them
_argv, sys.argv = sys.argv, sys.argv[:1]
import FreeCAD as App  # noqa: E402
import Part  # noqa: E402
sys.argv = _argv


def read_solids(path):
    """[(default name, solid), ...]; FCStd solids are named after their object label."""
    if path.lower().endswith(".fcstd"):
        doc = App.openDocument(path)
        objs = [o for o in doc.Objects
                if hasattr(o, "Shape") and o.Shape.Solids and not o.InList]  # top-level only
        # no Part.makeCompound here: it silently kills some FreeCAD 1.x builds
        out = []
        for o in objs:
            sols = o.Shape.Solids
            out += [(o.Label if len(sols) == 1 else f"{o.Label}{k}", s) for k, s in enumerate(sols)]
        return out
    sh = Part.Shape()
    sh.read(path)
    return [(f"solid{k}", s) for k, s in enumerate(sh.Solids)]


def tris(solid, tol):
    v, f = solid.tessellate(tol)
    return [[[v[i].x, v[i].y, v[i].z] for i in t] for t in f]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--tol", type=float, default=0.02, help="tessellation tolerance (model units)")
    ap.add_argument("--names", help="comma separated names for the solids, in order")
    a = ap.parse_args()
    found = read_solids(a.input)
    solids = [s for _, s in found]
    names = a.names.split(",") if a.names else [n for n, _ in found]
    if len(names) != len(solids):
        sys.exit(f"{len(solids)} solids found but {len(names)} names given")
    with open(a.output, "w") as f:
        json.dump({n: tris(s, a.tol) for n, s in zip(names, solids)}, f)
    print(f"{a.output}: {', '.join(names)}")


if __name__ == "__main__":
    main()
