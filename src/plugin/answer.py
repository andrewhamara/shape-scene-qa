"""answer_key: a question's answer, from the objects detect_objects finds in the scene's image.

NanoAgent runs it before the agent, out of its sight, and the verifier checks it against the
scene's true objects. A question with no one answer on its scene is refused here, before any agent
runs.
"""

from __future__ import annotations

from pathlib import Path

from slimconfig import plain_output

from contract import AnswerKeyOutput, QuestionInput, SceneInput
from plugin.detect import detect_objects
from plugin.questions import anchor_problem, answer, words


def answer_key(given: QuestionInput, workspace: Path) -> AnswerKeyOutput:
    question = plain_output(given)
    problem = anchor_problem(question)
    if problem:
        raise ValueError(problem)
    scene = detect_objects(SceneInput(scene=given.scene), workspace)
    anchor, objects, reply = answer(plain_output(scene)["objects"], question)
    return AnswerKeyOutput(scene=given.scene, question=words(question), anchor=anchor, objects=objects, answer=reply)
