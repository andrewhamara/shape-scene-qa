from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw
from slimconfig import plain_output

from contract import SceneInput
from plugin import detect_objects
from plugin.detect import detect
from verifier.scenes import SCENES, SIDES


@pytest.mark.parametrize("scene", sorted(SCENES))
def test_finds_exactly_the_objects_each_scene_was_drawn_with(tmp_path: Path, scene: str) -> None:
    found = plain_output(detect_objects(SceneInput(scene=scene), tmp_path))
    assert (found["width"], found["height"]) == (480, 320)
    assert [{key: o[key] for key in ("id", "shape", "color", "size", "x", "y")} for o in found["objects"]] == list(
        SCENES[scene]
    )
    assert all(o["width"] == o["height"] == SIDES[o["size"]] for o in found["objects"])


def test_tells_apart_two_squares_of_one_color_2_px_apart(tmp_path: Path) -> None:
    found = detect_objects(SceneInput(scene="scene-40"), tmp_path).objects
    blue = [(o.x, o.shape.value) for o in found if o.color.value == "blue"]
    assert blue == [(100, "square"), (127, "square")]


@pytest.mark.parametrize("scene", ["scene-00", "scene-41", "scene-1", "../scene-01", ""])
def test_refuses_a_scene_that_is_not_bundled(tmp_path: Path, scene: str) -> None:
    with pytest.raises(ValueError, match="no scene"):
        detect_objects(SceneInput(scene=scene), tmp_path)


def test_refuses_a_color_outside_the_palette() -> None:
    image = Image.new("RGB", (100, 100), (255, 255, 255))
    ImageDraw.Draw(image).rectangle((10, 10, 34, 34), fill=(1, 2, 3))
    with pytest.raises(ValueError, match="not in the palette"):
        detect(image)


def test_refuses_a_region_of_another_size() -> None:
    image = Image.new("RGB", (100, 100), (255, 255, 255))
    ImageDraw.Draw(image).rectangle((10, 10, 39, 34), fill=(220, 40, 40))
    with pytest.raises(ValueError, match="neither 25 nor 51"):
        detect(image)
