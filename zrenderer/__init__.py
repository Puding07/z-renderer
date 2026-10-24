"""zrenderer - render triangle meshes to PNG with a tiny numpy z-buffer rasterizer."""
from .mesh import apply, load, load_json, rotate, scale, translate
from .render import camera, render
from .scene import figure, parse_color, run_scene, save_image

__version__ = "0.1.0"
__all__ = ["apply", "camera", "figure", "load", "load_json", "parse_color", "render",
           "rotate", "run_scene", "save_image", "scale", "translate"]
