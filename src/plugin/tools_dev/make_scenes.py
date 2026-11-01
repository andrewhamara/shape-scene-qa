"""Draws the bundled scenes, ui/scenes/scene-NN.png, and writes their true objects to verifier/scenes.py
and, for the page's pictures, ui/scenes.js.

    uv run python -m plugin.tools_dev.make_scenes

Scenes 01 to 36 are random from fixed seeds; 37 to 40 are drawn by hand for boundary cases. Each
image is checked before anything is written: detect_objects must find exactly the objects drawn.
Running it again writes the same files.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from PIL import Image, ImageDraw

from plugin.detect import PALETTE, SCENES, detect

ROOT = Path(__file__).resolve().parents[3]
TRUTH = ROOT / "verifier" / "scenes.py"
PAGE = ROOT / "ui" / "scenes.js"
WIDTH, HEIGHT = 480, 320
GAP = 6  # the fewest pixels between two random objects' boxes
RADIUS = {"small": 12, "large": 25}  # a side of 2 * radius + 1: 25 and 51 px
COLORS = {color.value: rgb for rgb, color in PALETTE.items()}
SHAPES = ("square", "circle", "triangle")

# Boundary scenes: (shape, color, size, x, y) of each object.
BY_HAND = {
    # A single object: the anchor cannot be another, counts are 0 or 1.
    37: [("triangle", "purple", "large", 240, 160)],
    # Three objects on the line x = 200: none of them is left or right of another.
    38: [
        ("square", "red", "small", 200, 60),
        ("circle", "blue", "large", 200, 160),
        ("triangle", "red", "small", 200, 260),
        ("square", "green", "large", 360, 160),
        ("circle", "yellow", "small", 80, 200),
    ],
    # Three objects 100 px from the gray square: nearest_to it has no one answer.
    39: [
        ("square", "gray", "large", 240, 160),
        ("circle", "red", "small", 140, 160),
        ("circle", "red", "small", 340, 160),
        ("triangle", "blue", "small", 240, 60),
        ("square", "yellow", "small", 60, 290),
    ],
    # Four objects on the line y = 120, two blue squares 2 px apart: neither above nor below,
    # and two shapes of one color that do not touch.
    40: [
        ("square", "blue", "small", 100, 120),
        ("square", "blue", "small", 127, 120),
        ("circle", "green", "large", 260, 120),
        ("triangle", "gray", "large", 400, 120),
        ("circle", "purple", "small", 260, 260),
        ("triangle", "red", "small", 60, 260),
    ],
}


def box(x: int, y: int, size: str) -> tuple[int, int, int, int]:
    r = RADIUS[size]
    return x - r, y - r, x + r, y + r


def random_scene(seed: int) -> list[tuple[str, str, str, int, int]]:
    rng = random.Random(seed)
    placed: list[tuple[str, str, str, int, int]] = []
    count = rng.randint(4, 9)
    while len(placed) < count:
        size = rng.choice(("small", "large"))
        r = RADIUS[size]
        x, y = rng.randint(r + 4, WIDTH - r - 5), rng.randint(r + 4, HEIGHT - r - 5)
        left, top, right, bottom = box(x, y, size)
        clear = all(
            right + GAP < other[0] or other[2] + GAP < left or bottom + GAP < other[1] or other[3] + GAP < top
            for other in (box(px, py, psize) for _, _, psize, px, py in placed)
        )
        if clear:
            placed.append((rng.choice(SHAPES), rng.choice(list(COLORS)), size, x, y))
    return placed


def draw(objects: list[tuple[str, str, str, int, int]]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
    pen = ImageDraw.Draw(image)
    for shape, color, size, x, y in objects:
        left, top, right, bottom = box(x, y, size)
        fill = COLORS[color]
        if shape == "square":
            pen.rectangle((left, top, right, bottom), fill=fill)
        elif shape == "circle":
            pen.ellipse((left, top, right, bottom), fill=fill)
        else:
            pen.polygon([(left, bottom), (right, bottom), (x, top)], fill=fill)
    return image


def truth(objects: list[tuple[str, str, str, int, int]]) -> list[dict]:
    """The objects in reading order with their ids, as the verifier holds them."""
    ordered = sorted(objects, key=lambda item: (item[4], item[3]))
    return [
        {"id": number, "shape": shape, "color": color, "size": size, "x": x, "y": y}
        for number, (shape, color, size, x, y) in enumerate(ordered, 1)
    ]


def main() -> None:
    scenes = {}
    for number in range(1, 41):
        objects = BY_HAND.get(number) or random_scene(2026_00 + number)
        image = draw(objects)
        expected = truth(objects)
        found = [
            {"id": o.id, "shape": o.shape.value, "color": o.color.value, "size": o.size.value, "x": o.x, "y": o.y}
            for o in detect(image)
        ]
        if found != expected:
            raise SystemExit(f"scene-{number:02d}: detect_objects finds {found}, not the drawn {expected}")
        scenes[f"scene-{number:02d}"] = (image, expected)
    SCENES.mkdir(exist_ok=True)
    for name, (image, _) in scenes.items():
        image.save(SCENES / f"{name}.png", optimize=True)
    lines = [
        '"""Each bundled scene\'s true objects, as src/plugin/tools_dev/make_scenes.py drew them. Generated: do not edit."""',
        "",
        f"WIDTH = {WIDTH}",
        f"HEIGHT = {HEIGHT}",
        "SIDES = {\"small\": 25, \"large\": 51}",
        "SCENES = {",
    ]
    for name, (_, expected) in scenes.items():
        lines.append(f"    {name!r}: (")
        lines += [f"        {item!r}," for item in expected]
        lines.append("    ),")
    lines.append("}")
    TRUTH.write_text("\n".join(lines) + "\n")
    page = [
        "// Each scene's objects, as src/plugin/tools_dev/make_scenes.py drew them, for renderers.js to box them",
        "// on the picture. Generated: do not edit.",
        f"export const WIDTH = {WIDTH};",
        f"export const HEIGHT = {HEIGHT};",
        "export const SIDES = { small: 25, large: 51 };",
        "export const SCENES = {",
    ]
    for name, (_, expected) in scenes.items():
        page.append(f'  "{name}": [')
        page += [f"    {json.dumps(item)}," for item in expected]
        page.append("  ],")
    page.append("};")
    PAGE.write_text("\n".join(page) + "\n")
    print(f"wrote {len(scenes)} scenes to {SCENES}, {TRUTH} and {PAGE}")


if __name__ == "__main__":
    main()
