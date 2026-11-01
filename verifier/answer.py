"""answer_key: the answer it pins is the one the scene's true objects give."""

from .checks import plain_question, question_problem, result
from .questions import IllPosed, answer
from .scenes import SCENES


def verify_input(value):
    problem = question_problem(value)
    if problem:
        return result(False, problem)
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    """``output_value``: a contract AnswerKeyOutput, held to the answer the true objects give."""
    try:
        anchor, objects, reply = answer(SCENES[input_value.scene], plain_question(input_value))
    except IllPosed as error:
        return result(False, f"the question has no one answer, so the answer key should refuse it: {error}")
    pinned = (output_value.scene, output_value.anchor, list(output_value.objects), output_value.answer)
    if pinned != (input_value.scene, anchor, objects, reply):
        return result(
            False,
            f"the answer key pins anchor {output_value.anchor}, objects {list(output_value.objects)} and answer "
            f"{output_value.answer!r}; the true objects give anchor {anchor}, objects {objects} and answer {reply!r}",
        )
    return result(True, f"the answer key is right: {reply}")
