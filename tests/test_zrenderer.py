import json
import os
import subprocess
import sys

import numpy as np

import zrenderer as z

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRI = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]],
                [[0, 0, 0], [0, 1, 0], [0, 0, 1]]], float)


def test_render_draws_model_on_background():
    img = z.render([(TRI, (1, 0, 0))], 30, -55, width=64, height=64)
    assert img.shape == (64, 64, 3)
    red = (img[..., 0] > 0.2) & (img[..., 1] < 0.05)
    assert 100 < red.sum() < 64 * 64
    assert np.allclose(img[0, 0], 1)                      # white corner


def test_bed_adds_grey_pixels():
    img = z.render([(TRI, (1, 0, 0))], 30, -55, bed=True, width=64, height=64)
    grey = np.isclose(img[..., 0], img[..., 1]) & np.isclose(img[..., 1], img[..., 2]) & (img[..., 0] < 0.99)
    assert grey.sum() > 50


def test_stl_ascii_binary_and_obj_roundtrip(tmp_path):
    a = tmp_path / "a.stl"
    a.write_text("solid t\n" + "".join(
        "facet normal 0 0 1\nouter loop\n" + "".join(f"vertex {x} {y} {zz}\n" for x, y, zz in t)
        + "endloop\nendfacet\n" for t in TRI) + "endsolid t\n")
    assert np.allclose(z.load(str(a)), TRI)

    rec = np.zeros(2, np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")]))
    rec["v"] = TRI
    b = tmp_path / "b.stl"
    b.write_bytes(b"solid but binary".ljust(80, b"\0") + np.uint32(2).tobytes() + rec.tobytes())
    assert np.allclose(z.load(str(b)), TRI)

    o = tmp_path / "c.obj"
    o.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nv 1 1 0\nf 1/1 2/2 4/4 3/3\n")
    assert z.load(str(o)).shape == (2, 3, 3)


def test_transforms():
    r = z.rotate(TRI, [0, 0, 1], 90)
    assert np.allclose(r[0, 1], [0, 1, 0])
    t = z.apply(TRI, [{"rotate": {"axis": [0, 0, 1], "angle": 90}}, {"translate": [0, 0, 5]}])
    assert np.allclose(t[0, 1], [0, 1, 5])


def test_parse_color():
    assert z.parse_color("#ff0000") == (1, 0, 0)
    assert z.parse_color([0, 255, 0]) == (0, 1, 0)
    assert z.parse_color([0.1, 0.2, 0.3]) == (0.1, 0.2, 0.3)


def test_scene_and_cli(tmp_path):
    (tmp_path / "m.json").write_text(json.dumps({"a": TRI.tolist(), "b": (TRI + 2).tolist()}))
    (tmp_path / "scene.json").write_text(json.dumps({
        "defaults": {"width": 80, "height": 80},
        "models": {"a": {"file": "m.json"}, "bb": {"file": "m.json", "key": "b", "color": "#00ff00"}},
        "figures": [{"output": "f.png", "panels": [
            {"parts": ["a", {"model": "bb", "transform": [{"translate": [1, 0, 0]}]}], "title": "x"},
            {"parts": ["a"], "bed": True}]}]}))
    out = z.run_scene(str(tmp_path / "scene.json"), log=lambda _: None)
    assert os.path.getsize(out[0]) > 0

    png = tmp_path / "cli.png"
    subprocess.run([sys.executable, "-m", "zrenderer", str(tmp_path / "m.json"), "-o", str(png),
                    "--size", "40x40"], check=False, cwd=ROOT)
    # m.json holds two meshes, so the plain CLI must refuse it
    assert not png.exists()
    subprocess.run([sys.executable, "-m", "zrenderer", os.path.join(ROOT, "examples/demo/nut.stl"),
                    "-o", str(png), "--size", "40x40", "--view", "20,-40", "--view", "60,10"],
                   check=True, cwd=ROOT)
    assert png.exists()
