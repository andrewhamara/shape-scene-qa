"""The scene-question task's verdict: the submitted answer against the one the scene's true objects give.

Eight constraints, in order; every one must hold. Each is {id, constraint, ok, expected, actual,
message}: ok is true, false, or null when a constraint it needs did not hold. Any failure of 1 to 6
scores 0; otherwise the score is half the F1 of the submitted objects and half the answer, at most
0.99 unless all eight hold.
"""

from .checks import plain_question, question_problem, result
from .questions import IllPosed, answer, answer_problem, words
from .scenes import SCENES

CONSTRAINTS = (
    ("question", "The question is well formed and its scene exists"),
    ("well-posed", "The question has one answer on its scene"),
    ("answer-key", "The answer key pinned the answer the scene's true objects give"),
    ("same-scene", "The submission is for the question's scene"),
    ("answer-form", "The answer has the form its ask needs"),
    ("objects-known", "The submitted objects are the scene's, each once"),
    ("objects-exact", "The submitted objects are exactly those the question picks out"),
    ("answer-exact", "The answer is right"),
)
GUARDS = 6  # constraints 1 to 6: a failure scores 0


def f1(found, expected):
    if not found and not expected:
        return 1.0
    hits = len(set(found) & set(expected))
    if not hits:
        return 0.0
    precision, recall = hits / len(set(found)), hits / len(set(expected))
    return 2 * precision * recall / (precision + recall)


def verify_task(arguments, output, reference, workspace):
    """``arguments``: a contract QuestionInput; ``output``: AnswerOutput; ``reference``: AnswerKeyOutput or None."""
    checks = {}

    def put(key, ok, expected=None, actual=None, message=""):
        checks[key] = {"ok": ok, "expected": expected, "actual": actual, "message": "" if ok else message}

    scene, question = arguments.scene, plain_question(arguments)
    problem = question_problem(arguments)
    put("question", problem is None, message=problem)
    truth = None
    if problem is None:
        try:
            truth = answer(SCENES[scene], question)
        except IllPosed as error:
            put("well-posed", False, message=f"{words(question)} {error}.")
        else:
            put("well-posed", True)
    if truth is not None:
        anchor, objects, reply = truth
        expected = {"anchor": anchor, "objects": objects, "answer": reply}
        if reference is None:
            put("answer-key", False, expected, None, "No answer key: answer_key never ran for this question.")
        else:
            pinned = {"anchor": reference.anchor, "objects": list(reference.objects), "answer": reference.answer}
            same = reference.scene == scene and pinned == expected
            put("answer-key", same, expected, pinned, f"The answer key for {reference.scene} disagrees with the truth.")
    put(
        "same-scene",
        output.scene == scene,
        scene,
        output.scene,
        f"The submission is for {output.scene!r}, not {scene!r}.",
    )
    if problem is None:
        form = answer_problem(question["ask"], output.answer)
        put("answer-form", form is None, actual=output.answer, message=f"The answer is malformed: {form}.")
    known = {item["id"] for item in SCENES[scene]} if problem is None else set()
    if problem is None:
        submitted = list(output.objects)
        unknown = sorted({number for number in submitted if number not in known})
        twice = sorted({number for number in submitted if submitted.count(number) > 1})
        message = (
            f"{scene} has no object {', '.join(map(str, unknown))} (its ids are 1 to {len(known)})."
            if unknown
            else f"Object {', '.join(map(str, twice))} is submitted more than once."
        )
        put("objects-known", not unknown and not twice, actual=submitted, message=message)
    if truth is not None and checks["objects-known"]["ok"]:
        found = sorted(output.objects)
        missed = [number for number in objects if number not in found]
        extra = [number for number in found if number not in objects]
        message = "; ".join(
            part
            for part in (
                f"misses {', '.join(map(str, missed))}" if missed else "",
                f"wrongly includes {', '.join(map(str, extra))}" if extra else "",
            )
            if part
        )
        put("objects-exact", found == objects, objects, found, f"{words(question)} The submission {message}.")
    if truth is not None and checks["answer-form"]["ok"]:
        put(
            "answer-exact",
            output.answer == reply,
            reply,
            output.answer,
            f"{words(question)} The answer is {reply!r}, not {output.answer!r}.",
        )

    constraints = []
    for key, text in CONSTRAINTS:
        check = checks.get(key)
        if check is None:
            waiting = next(k for k, _ in CONSTRAINTS if checks.get(k, {"ok": True})["ok"] is False)
            check = {"ok": None, "expected": None, "actual": None, "message": f"Not checked: {waiting} did not hold."}
        constraints.append({"id": key, "constraint": text, **check})
    failed = [item for item in constraints if item["ok"] is False]
    details = {"constraints": constraints, "question": words(question) if problem is None else None}
    if truth is not None:
        details["expected"] = expected
    if not failed:
        return result(True, f"All {len(CONSTRAINTS)} checks hold: {words(question)} {reply}.", **details)
    first = failed[0]
    message = f"{first['id']}: {first['message']}" + (f" (+{len(failed) - 1} more)" if len(failed) > 1 else "")
    guard_failed = any(item["ok"] is not True for item in constraints[:GUARDS])
    if guard_failed:
        return result(False, message, score=0.0, **details)
    overlap = f1(output.objects, objects)
    score = min(0.99, 0.5 * overlap + 0.5 * (output.answer == reply))
    return result(False, message, score=round(score, 4), f1=round(overlap, 4), **details)
