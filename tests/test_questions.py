from __future__ import annotations

from pathlib import Path

import pytest

from plugin.questions import IllPosed, answer, answer_problem, words

ROOT = Path(__file__).resolve().parents[1]
ANY = {"color": "any", "shape": "any", "size": "any"}


def thing(number, shape, color, size, x, y):
    return {"id": number, "shape": shape, "color": color, "size": size, "x": x, "y": y}


OBJECTS = [
    thing(1, "square", "red", "small", 100, 50),
    thing(2, "circle", "blue", "large", 200, 100),
    thing(3, "triangle", "red", "large", 200, 200),
    thing(4, "square", "red", "small", 300, 150),
]


def question(ask, relation="anywhere", target=None, anchor=None):
    return {"ask": ask, "target": ANY | (target or {}), "relation": relation, "anchor": ANY | (anchor or {})}


def test_the_verifier_answers_by_a_byte_for_byte_copy_of_the_rules() -> None:
    assert (ROOT / "verifier/questions.py").read_bytes() == (ROOT / "src/plugin/questions.py").read_bytes()


@pytest.mark.parametrize(
    ("asked", "expected"),
    [
        (question("count", target={"color": "red"}), (0, [1, 3, 4], "3")),
        (question("count", "left_of", {"color": "red"}, {"color": "blue"}), (2, [1], "1")),
        (question("exists", "below", {"shape": "square"}, {"shape": "circle"}), (2, [4], "yes")),
        (question("exists", "above", {"shape": "triangle"}, {"shape": "circle"}), (2, [], "no")),
        (question("color", "nearest_to", anchor={"shape": "circle"}), (2, [3], "red")),
        (question("count", "nearest_to", {"color": "green"}, {"shape": "circle"}), (2, [], "0")),
        (question("size", "right_of", {"color": "red"}, {"shape": "triangle"}), (3, [4], "small")),
    ],
)
def test_answers_by_the_rules(asked: dict, expected: tuple) -> None:
    assert answer(OBJECTS, asked) == expected


def test_an_object_on_the_anchors_line_is_neither_left_nor_right_nor_the_anchor_itself() -> None:
    # Object 3 shares the circle's x = 200; the circle is never its own target.
    assert answer(OBJECTS, question("count", "left_of", anchor={"shape": "circle"}))[1:] == ([1], "1")
    assert answer(OBJECTS, question("count", "right_of", anchor={"shape": "circle"}))[1:] == ([4], "1")


@pytest.mark.parametrize(
    ("asked", "reason"),
    [
        (question("count", "left_of", anchor={"color": "red"}), "3 objects are red objects"),
        (question("count", "left_of", anchor={"color": "green"}), "0 objects are green objects"),
        (question("shape", target={"color": "red"}), "3 objects are picked out"),
        (question("shape", target={"color": "green"}), "0 objects are picked out"),
        # Squares 1 and 4 are both 100 px across and 50 px up or down from the circle.
        (question("color", "nearest_to", {"shape": "square"}, {"shape": "circle"}), "equally near"),
    ],
)
def test_refuses_a_question_with_no_one_answer(asked: dict, reason: str) -> None:
    with pytest.raises(IllPosed, match=reason):
        answer(OBJECTS, asked)


def test_words() -> None:
    asked = question("count", "left_of", {"color": "red"}, {"color": "blue", "shape": "square", "size": "large"})
    assert words(asked) == "How many red objects are left of the large blue square?"
    assert words(question("exists", target={"shape": "circle"})) == "Is there a circle in the scene?"
    assert words(question("color", "nearest_to", anchor={"shape": "circle"})) == (
        "What color is the object nearest to the circle?"
    )


@pytest.mark.parametrize(
    ("ask", "reply", "ok"),
    [
        ("count", "0", True),
        ("count", "12", True),
        ("count", "03", False),
        ("count", "three", False),
        ("count", "-1", False),
        ("count", "", False),
        ("count", "٣", False),
        ("exists", "yes", True),
        ("exists", "Yes", False),
        ("exists", "true", False),
        ("color", "gray", True),
        ("color", "grey", False),
        ("shape", "circle", True),
        ("size", "big", False),
    ],
)
def test_holds_answers_to_their_form(ask: str, reply: str, ok: bool) -> None:
    assert (answer_problem(ask, reply) is None) == ok
