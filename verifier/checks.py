"""Checks shared by the verifiers. Pure functions of contract instances and the scenes' truth."""

from .questions import anchor_problem
from .scenes import SCENES


def result(valid, message, *, score=None, **details):
    return {
        "valid": valid,
        "score": float(valid) if score is None else score,
        "message": message,
        "details": details,
    }


def scene_problem(scene):
    if scene not in SCENES:
        return f"no scene {scene!r}: the scenes are scene-01 to scene-40"
    return None


def plain_filter(wanted):
    return {"color": wanted.color.value, "shape": wanted.shape.value, "size": wanted.size.value}


def plain_question(value):
    """A contract QuestionInput as questions.py takes it."""
    return {
        "ask": value.ask.value,
        "target": plain_filter(value.target),
        "relation": value.relation.value,
        "anchor": plain_filter(value.anchor),
    }


def question_problem(value):
    """What is wrong with a contract QuestionInput whatever its scene's objects, or None."""
    return scene_problem(value.scene) or anchor_problem(plain_question(value))
