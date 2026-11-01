from __future__ import annotations

from pathlib import Path

import pytest
from slimconfig import build_output, plain_output

import verifier
from contract import TASKS, TOOLS, AnswerKeyOutput, QuestionInput, SceneInput, Task, Tool
from plugin import answer_key, detect_objects

ANY = {"color": "any", "shape": "any", "size": "any"}
# scene-02: gray triangle 2, gray squares 3 and 4 are left of the green triangle 5.
GRAY_LEFT_OF_GREEN = {
    "scene": "scene-02",
    "ask": "count",
    "target": ANY | {"color": "gray"},
    "relation": "left_of",
    "anchor": ANY | {"color": "green"},
}


# The verifier gets contract instances, as NanoAgent's sandbox builds them from JSON.
def verify_input(tool: str, value: dict) -> dict:
    return verifier.verify_input(tool, build_output(value, TOOLS[Tool(tool)][0]))


def verify_output(tool: str, given: dict, made: dict) -> dict:
    classes = TOOLS[Tool(tool)]
    return verifier.verify_output(tool, build_output(given, classes[0]), build_output(made, classes[1]), ".")


def key_for(question: dict) -> dict:
    return plain_output(answer_key(build_output(question, QuestionInput), Path(".")))


def verify_task(question: dict, output: dict, reference: dict | None = None, *, pinned: bool = True) -> dict:
    given, made = TASKS[Task.SCENE_QUESTION]
    if pinned and reference is None:
        reference = key_for(question)
    key = None if reference is None else build_output(reference, AnswerKeyOutput)
    return verifier.verify_task(
        "scene-question", build_output(question, given), build_output(output, made), key, "."
    )


def ids(verdict: dict) -> dict:
    return {item["id"]: item["ok"] for item in verdict["details"]["constraints"]}


# Correct


def test_approves_the_right_answer_and_objects() -> None:
    verdict = verify_task(GRAY_LEFT_OF_GREEN, {"scene": "scene-02", "objects": [2, 3, 4], "answer": "3"})
    assert verdict["valid"] is True and verdict["score"] == 1.0
    assert verdict["message"] == "All 8 checks hold: How many gray objects are left of the green object? 3."
    assert set(ids(verdict).values()) == {True}


def test_objects_may_come_in_any_order() -> None:
    verdict = verify_task(GRAY_LEFT_OF_GREEN, {"scene": "scene-02", "objects": [4, 2, 3], "answer": "3"})
    assert verdict["valid"] is True


# Incorrect


def test_a_wrong_answer_with_the_right_objects_scores_half() -> None:
    verdict = verify_task(GRAY_LEFT_OF_GREEN, {"scene": "scene-02", "objects": [2, 3, 4], "answer": "2"})
    assert verdict["valid"] is False and verdict["score"] == 0.5
    assert verdict["message"].startswith("answer-exact:") and "The answer is '3', not '2'" in verdict["message"]


def test_a_right_answer_on_the_wrong_objects_is_partly_credited() -> None:
    # Three objects, but 1 (the purple square) instead of 4.
    verdict = verify_task(GRAY_LEFT_OF_GREEN, {"scene": "scene-02", "objects": [1, 2, 3], "answer": "3"})
    assert verdict["valid"] is False and verdict["score"] == pytest.approx(0.5 + 0.5 * 2 / 3, abs=1e-4)
    assert "misses 4; wrongly includes 1" in verdict["message"]


def test_the_wrong_scene_scores_zero() -> None:
    verdict = verify_task(GRAY_LEFT_OF_GREEN, {"scene": "scene-03", "objects": [2, 3, 4], "answer": "3"})
    assert verdict["valid"] is False and verdict["score"] == 0.0 and verdict["message"].startswith("same-scene:")


# Missing


def test_an_empty_answer_is_malformed_and_scores_zero() -> None:
    verdict = verify_task(GRAY_LEFT_OF_GREEN, {"scene": "scene-02", "objects": [], "answer": ""})
    assert verdict["valid"] is False and verdict["score"] == 0.0
    assert verdict["message"].startswith("answer-form:")
    assert ids(verdict)["answer-exact"] is None


def test_no_objects_when_some_are_picked_out_is_partly_wrong() -> None:
    verdict = verify_task(GRAY_LEFT_OF_GREEN, {"scene": "scene-02", "objects": [], "answer": "3"})
    assert verdict["valid"] is False and verdict["score"] == 0.5 and "misses 2, 3, 4" in verdict["message"]


def test_no_answer_key_scores_zero() -> None:
    verdict = verify_task(GRAY_LEFT_OF_GREEN, {"scene": "scene-02", "objects": [2, 3, 4], "answer": "3"}, pinned=False)
    assert verdict["valid"] is False and verdict["score"] == 0.0
    assert verdict["message"].startswith("answer-key: No answer key")


# Malformed


@pytest.mark.parametrize("reply", ["three", "03", "3 objects", " 3", "Three"])
def test_a_count_not_in_digits_is_malformed(reply: str) -> None:
    verdict = verify_task(GRAY_LEFT_OF_GREEN, {"scene": "scene-02", "objects": [2, 3, 4], "answer": reply})
    assert verdict["valid"] is False and verdict["score"] == 0.0 and verdict["message"].startswith("answer-form:")


@pytest.mark.parametrize(("objects", "message"), [([2, 3, 99], "no object 99"), ([2, 3, 3, 4], "Object 3 is submitted")])
def test_unknown_or_repeated_objects_are_malformed(objects: list, message: str) -> None:
    verdict = verify_task(GRAY_LEFT_OF_GREEN, {"scene": "scene-02", "objects": objects, "answer": "3"})
    assert verdict["valid"] is False and verdict["score"] == 0.0 and message in verdict["message"]


def test_an_answer_key_that_disagrees_with_the_truth_fails_the_run() -> None:
    wrong_key = key_for(GRAY_LEFT_OF_GREEN) | {"answer": "2", "objects": [2, 3]}
    verdict = verify_task(GRAY_LEFT_OF_GREEN, {"scene": "scene-02", "objects": [2, 3, 4], "answer": "3"}, wrong_key)
    assert verdict["valid"] is False and verdict["score"] == 0.0 and verdict["message"].startswith("answer-key:")


# Boundary


def test_an_object_on_the_anchors_line_is_not_left_of_it() -> None:
    # scene-38: red square 1, blue circle 2 and red triangle 5 all have x = 200.
    question = {
        "scene": "scene-38",
        "ask": "count",
        "target": ANY | {"color": "red"},
        "relation": "left_of",
        "anchor": ANY | {"color": "blue"},
    }
    assert key_for(question)["answer"] == "0"
    assert verify_task(question, {"scene": "scene-38", "objects": [], "answer": "0"})["valid"] is True
    verdict = verify_task(question, {"scene": "scene-38", "objects": [1, 5], "answer": "2"})
    assert verdict["valid"] is False and "wrongly includes 1, 5" in verdict["message"]


def test_a_scene_of_one_object_counts_zero_targets_anywhere_else() -> None:
    question = {"scene": "scene-37", "ask": "exists", "target": ANY, "relation": "below", "anchor": ANY | {"shape": "triangle"}}
    assert verify_task(question, {"scene": "scene-37", "objects": [], "answer": "no"})["valid"] is True
    assert verify_task(question, {"scene": "scene-37", "objects": [1], "answer": "yes"})["valid"] is False


def test_a_tie_for_nearest_is_refused_by_the_answer_key_and_the_verifier() -> None:
    # scene-39: three objects are each 100 px from the gray square.
    question = {"scene": "scene-39", "ask": "color", "target": ANY, "relation": "nearest_to", "anchor": ANY | {"color": "gray"}}
    with pytest.raises(ValueError, match="equally near"):
        key_for(question)
    verdict = verify_task(question, {"scene": "scene-39", "objects": [2], "answer": "red"}, pinned=False)
    assert verdict["valid"] is False and verdict["score"] == 0.0 and verdict["message"].startswith("well-posed:")


def test_a_question_that_picks_out_nothing_has_answer_zero() -> None:
    question = {"scene": "scene-40", "ask": "count", "target": ANY, "relation": "above", "anchor": ANY | {"color": "green"}}
    assert verify_task(question, {"scene": "scene-40", "objects": [], "answer": "0"})["valid"] is True


# Tool calls


def test_checks_tool_inputs() -> None:
    assert verify_input("detect_objects", {"scene": "scene-01"})["valid"] is True
    assert verify_input("detect_objects", {"scene": "scene-41"})["valid"] is False
    assert verify_input("answer_key", GRAY_LEFT_OF_GREEN)["valid"] is True
    no_anchor = GRAY_LEFT_OF_GREEN | {"anchor": ANY}
    assert "must name its color" in verify_input("answer_key", no_anchor)["message"]
    stray_anchor = GRAY_LEFT_OF_GREEN | {"relation": "anywhere"}
    assert "must be all any" in verify_input("answer_key", stray_anchor)["message"]


def test_holds_detect_objects_to_the_drawn_scene() -> None:
    found = plain_output(detect_objects(SceneInput(scene="scene-02"), Path(".")))
    assert verify_output("detect_objects", {"scene": "scene-02"}, found)["valid"] is True
    recolored = found | {"objects": [found["objects"][0] | {"color": "red"}, *found["objects"][1:]]}
    assert "color 'red' instead of 'purple'" in verify_output("detect_objects", {"scene": "scene-02"}, recolored)["message"]
    dropped = found | {"objects": found["objects"][:-1]}
    assert "has 7 objects, not 6" in verify_output("detect_objects", {"scene": "scene-02"}, dropped)["message"]
    resized = found | {"objects": [found["objects"][0] | {"width": 50}, *found["objects"][1:]]}
    assert verify_output("detect_objects", {"scene": "scene-02"}, resized)["valid"] is False
    other = verify_output("detect_objects", {"scene": "scene-03"}, found)
    assert other["valid"] is False


def test_holds_answer_key_to_the_truth() -> None:
    key = key_for(GRAY_LEFT_OF_GREEN)
    assert verify_output("answer_key", GRAY_LEFT_OF_GREEN, key)["valid"] is True
    assert verify_output("answer_key", GRAY_LEFT_OF_GREEN, key | {"answer": "4"})["valid"] is False
    assert verify_output("answer_key", GRAY_LEFT_OF_GREEN, key | {"anchor": 1})["valid"] is False


def test_the_detect_objects_task_is_judged_as_its_tool() -> None:
    found = plain_output(detect_objects(SceneInput(scene="scene-05"), Path(".")))
    given, made = TASKS[Task.DETECT_OBJECTS]
    verdict = verifier.verify_task("detect-objects", build_output({"scene": "scene-05"}, given), build_output(found, made), None, ".")
    assert verdict["valid"] is True


def test_the_verdict_is_the_same_twice() -> None:
    output = {"scene": "scene-02", "objects": [1, 3], "answer": "two"}
    assert verify_task(GRAY_LEFT_OF_GREEN, output) == verify_task(GRAY_LEFT_OF_GREEN, output)
