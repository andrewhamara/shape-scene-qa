"""detect_objects: every object it reports is one drawn in the scene, and every one drawn is reported."""

from .checks import result, scene_problem
from .scenes import HEIGHT, SCENES, SIDES, WIDTH

FIELDS = ("id", "shape", "color", "size", "x", "y")


def verify_input(value):
    problem = scene_problem(value.scene)
    if problem:
        return result(False, problem)
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    """``output_value``: a contract SceneOutput, held to the scene's true objects."""
    scene = input_value.scene
    if output_value.scene != scene:
        return result(False, f"the output is for {output_value.scene!r}, not {scene!r}")
    if (output_value.width, output_value.height) != (WIDTH, HEIGHT):
        return result(False, f"the image is {WIDTH}x{HEIGHT} px, not {output_value.width}x{output_value.height}")
    found = [
        {"id": o.id, "shape": o.shape.value, "color": o.color.value, "size": o.size.value, "x": o.x, "y": o.y}
        for o in output_value.objects
    ]
    drawn = list(SCENES[scene])
    for item, true in zip(found, drawn):
        if item != true:
            wrong = [f"{key} {item[key]!r} instead of {true[key]!r}" for key in FIELDS if item[key] != true[key]]
            return result(False, f"object {true['id']} of {scene} is reported with {', '.join(wrong)}")
    if len(found) != len(drawn):
        return result(False, f"{scene} has {len(drawn)} objects, not {len(found)}")
    for o in output_value.objects:
        side = SIDES[o.size.value]
        if (o.width, o.height) != (side, side):
            return result(False, f"object {o.id} is {o.size.value}, {side}x{side} px, not {o.width}x{o.height}")
    return result(True, f"all {len(drawn)} objects of {scene} are reported as drawn", objects=len(drawn))
