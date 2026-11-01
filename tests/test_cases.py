"""A scripted agent, no model: on every scene, many questions, each run as NanoAgent runs the task.

answer_key pins the answer first; the scripted agent then calls detect_objects and answers from
its objects by the task's instructions, written here again independently of questions.py; the
verifier judges the submission. Every well-posed question must pass, and every question the answer
key refuses must be one the scripted agent also finds has no one answer.
"""

from __future__ import annotations

import itertools
from pathlib import Path

import pytest
from slimconfig import build_output, plain_output

import verifier
from contract import AnswerKeyOutput, AnswerOutput, QuestionInput, SceneInput
from plugin import answer_key, detect_objects
from verifier.scenes import SCENES

ANY = {"color": "any", "shape": "any", "size": "any"}
RELATIONS = ("anywhere", "left_of", "right_of", "above", "below", "nearest_to")
ASKS = ("count", "exists", "color", "shape", "size")


class NoOneAnswer(Exception):
    pass


def scripted_agent(scene: dict, question: dict) -> dict:
    """The task's instructions, followed by hand, from detect_objects's output."""

    def fits(item, wanted):
        return all(value in ("any", item[key]) for key, value in wanted.items())

    objects = scene["objects"]
    anchor = None
    if question["relation"] != "anywhere":
        anchors = [item for item in objects if fits(item, question["anchor"])]
        if len(anchors) != 1:
            raise NoOneAnswer
        anchor = anchors[0]
    targets = [item for item in objects if fits(item, question["target"]) and item["id"] != (anchor or {}).get("id")]
    relation = question["relation"]
    if relation == "left_of":
        targets = [item for item in targets if item["x"] < anchor["x"]]
    elif relation == "right_of":
        targets = [item for item in targets if item["x"] > anchor["x"]]
    elif relation == "above":
        targets = [item for item in targets if item["y"] < anchor["y"]]
    elif relation == "below":
        targets = [item for item in targets if item["y"] > anchor["y"]]
    elif relation == "nearest_to" and targets:
        by_distance = sorted(targets, key=lambda item: (item["x"] - anchor["x"]) ** 2 + (item["y"] - anchor["y"]) ** 2)
        first = by_distance[0]
        nearest = (first["x"] - anchor["x"]) ** 2 + (first["y"] - anchor["y"]) ** 2
        if len(by_distance) > 1 and (by_distance[1]["x"] - anchor["x"]) ** 2 + (
            by_distance[1]["y"] - anchor["y"]
        ) ** 2 == nearest:
            raise NoOneAnswer
        targets = [first]
    ask = question["ask"]
    if ask == "count":
        reply = str(len(targets))
    elif ask == "exists":
        reply = "yes" if targets else "no"
    elif len(targets) != 1:
        raise NoOneAnswer
    else:
        reply = targets[0][ask]
    return {"scene": scene["scene"], "objects": sorted(item["id"] for item in targets), "answer": reply}


def questions(scene: str):
    """Questions about the scene: each ask and relation, targets by each color and shape present, anchors by
    each object's full description and by its color alone."""
    objects = SCENES[scene]
    targets = [ANY] + [ANY | {"color": c} for c in sorted({o["color"] for o in objects})]
    targets += [ANY | {"shape": s} for s in sorted({o["shape"] for o in objects})]
    anchors = [{key: o[key] for key in ("color", "shape", "size")} for o in objects]
    anchors += [ANY | {"color": o["color"]} for o in objects]
    anchors = [dict(pairs) for pairs in sorted({tuple(sorted(anchor.items())) for anchor in anchors})]
    for ask, relation, target in itertools.product(ASKS, RELATIONS, targets):
        for anchor in [ANY] if relation == "anywhere" else anchors:
            yield {"scene": scene, "ask": ask, "target": target, "relation": relation, "anchor": anchor}


@pytest.mark.parametrize("scene", sorted(SCENES))
def test_a_scripted_agent_passes_every_well_posed_question(tmp_path: Path, scene: str) -> None:
    passed = refused = 0
    seen = plain_output(detect_objects(SceneInput(scene=scene), tmp_path))
    for question in questions(scene):
        given = build_output(question, QuestionInput)
        try:
            key = answer_key(given, tmp_path)
        except ValueError:
            with pytest.raises(NoOneAnswer):
                scripted_agent(seen, question)
            refused += 1
            continue
        submitted = scripted_agent(seen, question)
        verdict = verifier.verify_task(
            "scene-question",
            given,
            build_output(submitted, AnswerOutput),
            build_output(plain_output(key), AnswerKeyOutput),
            str(tmp_path),
        )
        assert verdict["valid"] is True, (question, verdict["message"])
        passed += 1
    assert passed > 0
    print(f"{scene}: {passed} questions pass, {refused} refused as having no one answer")
