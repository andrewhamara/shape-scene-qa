"""detect_objects: every object in a bundled scene's image, found in its pixels.

An object is a 4-connected region of one palette color on the white background. Its size is its
bounding box (25 or 51 px square), its shape how much of that box it fills (a square all of it, a
circle about 79%, a triangle about 55%), and its center the box's middle. Ids follow reading order:
top to bottom by y, then left to right by x. A pixel of any other color, or a region of any other
size or fill, is refused: the scenes hold nothing else.
"""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

from PIL import Image

from contract import Color, SceneInput, SceneObject, SceneOutput, Shape, Size

SCENES = Path(__file__).with_name("scenes")
SCENE_ID = re.compile(r"^scene-\d{2}$")
BACKGROUND = (255, 255, 255)
PALETTE = {
    (220, 40, 40): Color.RED,
    (40, 160, 70): Color.GREEN,
    (40, 90, 220): Color.BLUE,
    (235, 195, 30): Color.YELLOW,
    (140, 60, 180): Color.PURPLE,
    (128, 128, 128): Color.GRAY,
}
SIDES = {25: Size.SMALL, 51: Size.LARGE}


def scene_path(scene: str) -> Path:
    path = SCENES / f"{scene}.png"
    if not SCENE_ID.fullmatch(scene) or not path.is_file():
        raise ValueError(f"no scene {scene!r}: the scenes are scene-01 to scene-40")
    return path


def shape_of(filled: int, side: int) -> Shape:
    share = filled / (side * side)
    if share > 0.95:
        return Shape.SQUARE
    if 0.7 < share < 0.9:
        return Shape.CIRCLE
    if 0.45 < share < 0.65:
        return Shape.TRIANGLE
    raise ValueError(f"a region fills {share:.0%} of its box, which is no square, circle or triangle")


def regions(image: Image.Image) -> list[tuple[tuple[int, int, int], list[tuple[int, int]]]]:
    """Each 4-connected region of one color other than the background: (its color, its pixels)."""
    width, height = image.size
    pixels = image.load()
    seen = [[False] * width for _ in range(height)]
    found = []
    for top in range(height):
        for left in range(width):
            color = pixels[left, top]
            if seen[top][left] or color == BACKGROUND:
                continue
            seen[top][left] = True
            stack, region = [(left, top)], []
            while stack:
                x, y = stack.pop()
                region.append((x, y))
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < width and 0 <= ny < height and not seen[ny][nx] and pixels[nx, ny] == color:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            found.append((color, region))
    return found


def detect(image: Image.Image) -> list[SceneObject]:
    objects = []
    for color, region in regions(image.convert("RGB")):
        if color not in PALETTE:
            raise ValueError(f"the color {color} at {region[0]} is not in the palette")
        xs, ys = [x for x, _ in region], [y for _, y in region]
        width, height = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
        if width != height or width not in SIDES:
            raise ValueError(f"a {width}x{height} px region at {region[0]} is neither 25 nor 51 px square")
        objects.append(
            SceneObject(
                id=0,
                shape=shape_of(len(region), width),
                color=PALETTE[color],
                size=SIDES[width],
                x=(min(xs) + max(xs)) // 2,
                y=(min(ys) + max(ys)) // 2,
                width=width,
                height=height,
            )
        )
    objects.sort(key=lambda item: (item.y, item.x))
    for number, item in enumerate(objects, 1):
        item.id = number
    return objects


@cache
def _detected(scene: str) -> tuple[int, int, tuple[tuple, ...]]:
    """The scene's image size and its objects' fields, read once: the bundled images never change."""
    with Image.open(scene_path(scene)) as image:
        width, height = image.size
        objects = detect(image)
    fields = tuple((o.id, o.shape, o.color, o.size, o.x, o.y, o.width, o.height) for o in objects)
    return width, height, fields


def detect_objects(given: SceneInput, workspace: Path) -> SceneOutput:
    """Every object in the scene's image, found in its pixels, in reading order."""
    width, height, fields = _detected(given.scene)
    keys = ("id", "shape", "color", "size", "x", "y", "width", "height")
    objects = [SceneObject(**dict(zip(keys, values))) for values in fields]
    return SceneOutput(scene=given.scene, width=width, height=height, objects=objects)
