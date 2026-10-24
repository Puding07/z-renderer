"""Mesh loading (STL / OBJ / JSON) and simple rigid transforms.

Every mesh is a numpy array of shape (N, 3, 3): N triangles x 3 vertices x xyz.
"""
import json
import os
import re

import numpy as np


def load(path, key=None):
    """Load a triangle mesh from .stl (ascii or binary), .obj or .json.

    JSON files hold either a list of triangles ``[[[x,y,z],[..],[..]], ...]`` or a dict
    of named meshes; for a dict, pass `key` to pick one (see :func:`load_json`).
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".stl":
        return load_stl(path)
    if ext == ".obj":
        return load_obj(path)
    if ext == ".json":
        meshes = load_json(path)
        if key is None:
            if len(meshes) != 1:
                raise ValueError(f"{path} holds several meshes {sorted(meshes)}; pick one with key")
            key = next(iter(meshes))
        return meshes[key]
    raise ValueError(f"unsupported mesh format: {path}")


def load_json(path):
    """Return {name: (N,3,3) array}. A bare triangle list is returned under its file stem."""
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict):
        return {k: np.asarray(v, float).reshape(-1, 3, 3) for k, v in data.items()}
    name = os.path.splitext(os.path.basename(path))[0]
    return {name: np.asarray(data, float).reshape(-1, 3, 3)}


def load_stl(path):
    with open(path, "rb") as f:
        raw = f.read()
    if len(raw) >= 84:
        n = int.from_bytes(raw[80:84], "little")
        if len(raw) == 84 + 50 * n:          # binary STL (some start with "solid" too)
            rec = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")])
            return np.frombuffer(raw, rec, n, 84)["v"].astype(float)
    nums = re.findall(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", raw)
    return np.array(nums, float).reshape(-1, 3, 3)


def load_obj(path):
    verts, tris = [], []
    with open(path) as f:
        for line in f:
            p = line.split()
            if not p:
                continue
            if p[0] == "v":
                verts.append([float(c) for c in p[1:4]])
            elif p[0] == "f":
                idx = [int(c.split("/")[0]) for c in p[1:]]
                idx = [i - 1 if i > 0 else len(verts) + i for i in idx]
                tris += [[idx[0], idx[k], idx[k + 1]] for k in range(1, len(idx) - 1)]
    return np.asarray(verts, float)[np.asarray(tris, int)]


def translate(tris, v):
    return tris + np.asarray(v, float)


def rotate(tris, axis, angle, center=(0, 0, 0)):
    """Rotate by `angle` degrees about `axis` through `center` (Rodrigues)."""
    k = np.asarray(axis, float); k = k / np.linalg.norm(k)
    t = np.radians(angle)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    R = np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * K @ K
    c = np.asarray(center, float)
    return (tris - c) @ R.T + c


def scale(tris, f, center=(0, 0, 0)):
    c = np.asarray(center, float)
    return (tris - c) * np.asarray(f, float) + c


def apply(tris, ops):
    """Apply a list of transform dicts in order, e.g.
    ``[{"rotate": {"axis": [1,0,0], "angle": 90}}, {"translate": [0,0,10]}]``."""
    for op in ops or []:
        for name, arg in op.items():
            if name == "translate":
                tris = translate(tris, arg)
            elif name == "rotate":
                tris = rotate(tris, **arg)
            elif name == "scale":
                tris = scale(tris, arg) if not isinstance(arg, dict) else scale(tris, **arg)
            else:
                raise ValueError(f"unknown transform: {name}")
    return tris
