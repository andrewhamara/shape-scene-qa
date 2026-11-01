"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    DETECT_OBJECTS = "detect_objects"
    ANSWER_KEY = "answer_key"


class Task(Enum):
    SCENE_QUESTION = "scene-question"
    DETECT_OBJECTS = "detect-objects"


class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"
    YELLOW = "yellow"
    PURPLE = "purple"
    GRAY = "gray"


class Shape(Enum):
    SQUARE = "square"
    CIRCLE = "circle"
    TRIANGLE = "triangle"


class Size(Enum):
    SMALL = "small"
    LARGE = "large"


class ColorChoice(Enum):
    ANY = "any"
    RED = "red"
    GREEN = "green"
    BLUE = "blue"
    YELLOW = "yellow"
    PURPLE = "purple"
    GRAY = "gray"


class ShapeChoice(Enum):
    ANY = "any"
    SQUARE = "square"
    CIRCLE = "circle"
    TRIANGLE = "triangle"


class SizeChoice(Enum):
    ANY = "any"
    SMALL = "small"
    LARGE = "large"


class Ask(Enum):
    COUNT = "count"
    EXISTS = "exists"
    COLOR = "color"
    SHAPE = "shape"
    SIZE = "size"


class Relation(Enum):
    ANYWHERE = "anywhere"
    LEFT_OF = "left_of"
    RIGHT_OF = "right_of"
    ABOVE = "above"
    BELOW = "below"
    NEAREST_TO = "nearest_to"


SCENE = "A bundled scene, scene-01 to scene-40"
OBJECT_ID = "An object's id: 1, 2, ... in reading order (top to bottom by y, then left to right by x)"
ANSWER = (
    'The answer, exactly in this form: count, the number in digits ("0", "3"); exists, "yes" or "no"; color, '
    'shape or size, the one object\'s value in lowercase ("red", "triangle", "large")'
)
MATCHED = "The ids of the objects the question picks out (the target objects that satisfy the relation), ascending"


@dataclass
class SceneInput(Output):
    scene: Annotated[str, SCENE]


@dataclass
class SceneObject(Output):
    id: Annotated[int, OBJECT_ID]
    shape: Shape
    color: Color
    size: Annotated[Size, "small (25 px across) or large (51 px across)"]
    x: Annotated[int, "The center's x in pixels from the left edge"]
    y: Annotated[int, "The center's y in pixels from the top edge: a larger y is lower in the image"]
    width: Annotated[int, "Width in pixels"]
    height: Annotated[int, "Height in pixels"]


@dataclass
class SceneOutput(Output):
    scene: Annotated[str, SCENE]
    width: Annotated[int, "The image's width in pixels"]
    height: Annotated[int, "The image's height in pixels"]
    objects: Annotated[list[SceneObject], "Every object detected in the image, in id order"]


@dataclass
class Filter(Output):
    color: Annotated[ColorChoice, "The color an object must have, or any"]
    shape: Annotated[ShapeChoice, "The shape an object must have, or any"]
    size: Annotated[SizeChoice, "The size an object must have, or any"]


@dataclass
class QuestionInput(Output):
    scene: Annotated[str, SCENE]
    ask: Annotated[Ask, "What to answer about the target objects: count, exists, or the color, shape or size of the one"]
    target: Annotated[Filter, "Which objects the question is about"]
    relation: Annotated[
        Relation,
        "Where the target objects must be relative to the anchor: anywhere (the anchor is then all any), left_of, "
        "right_of, above, below, or nearest_to (the one target object closest to the anchor)",
    ]
    anchor: Annotated[Filter, "The one reference object the relation is measured from; all any when anywhere"]


@dataclass
class AnswerKeyOutput(Output):
    scene: Annotated[str, SCENE]
    question: Annotated[str, "The question in words"]
    anchor: Annotated[int, "The anchor object's id; 0 when the relation is anywhere"]
    objects: Annotated[list[int], MATCHED]
    answer: Annotated[str, ANSWER]


@dataclass
class AnswerOutput(Output):
    scene: Annotated[str, SCENE]
    objects: Annotated[list[int], MATCHED]
    answer: Annotated[str, ANSWER]


TOOLS = {
    Tool.DETECT_OBJECTS: (SceneInput, SceneOutput),
    Tool.ANSWER_KEY: (QuestionInput, AnswerKeyOutput),
}
TASKS = {
    Task.SCENE_QUESTION: (QuestionInput, AnswerOutput),
    Task.DETECT_OBJECTS: (SceneInput, SceneOutput),
}
