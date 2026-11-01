"""A demo you can watch: questions about scenes, scripted submissions, and the verifier's verdicts. No model runs.

    uv run python -m plugin.tools_dev.demo

For each question it opens the scene with every detected object boxed and numbered (the anchor in
black, the objects the question picks out in orange), prints what detect_objects found, the
answer key, and how the verifier judges a right, a wrong and a malformed submission. The pictures
are saved in a temporary folder whose path it prints.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from slimconfig import build_output, plain_output

import verifier
from contract import AnswerKeyOutput, AnswerOutput, QuestionInput, SceneInput
from plugin import answer_key, detect_objects
from plugin.detect import scene_path
from plugin.questions import words

ANY = {"color": "any", "shape": "any", "size": "any"}
BOLD, DIM, GREEN, RED, ORANGE, RESET = "\033[1m", "\033[2m", "\033[32m", "\033[31m", "\033[33m", "\033[0m"
MARKS = {True: f"{GREEN}✓{RESET}", False: f"{RED}✗{RESET}", None: f"{DIM}·{RESET}"}
SCALE = 2
GRAY_BOX = (170, 170, 170)

# (what it shows, the question, the submissions to judge: (label, objects, answer))
DEMOS = [
    (
        "A counting question with a relation",
        {"scene": "scene-02", "ask": "count", "target": ANY | {"color": "gray"}, "relation": "left_of",
         "anchor": ANY | {"color": "green"}},
        [
            ("a right answer", [2, 3, 4], "3"),
            ("the right count on the wrong objects", [1, 2, 3], "3"),
            ("a wrong count", [2, 3], "2"),
            ("a malformed answer", [2, 3, 4], "three"),
        ],
    ),
    (
        "Boundary: three objects on the line x = 200 are not left of each other",
        {"scene": "scene-38", "ask": "count", "target": ANY | {"color": "red"}, "relation": "left_of",
         "anchor": ANY | {"color": "blue"}},
        [
            ("a right answer", [], "0"),
            ("counting objects on the anchor's line", [1, 5], "2"),
        ],
    ),
    (
        "An attribute question with nearest_to",
        {"scene": "scene-05", "ask": "shape", "target": ANY, "relation": "nearest_to",
         "anchor": ANY | {"color": "purple"}},
        [],
    ),
    (
        "Boundary: a tie for nearest has no one answer, so the answer key refuses it",
        {"scene": "scene-39", "ask": "color", "target": ANY, "relation": "nearest_to",
         "anchor": ANY | {"color": "gray"}},
        [],
    ),
]


def picture(scene: str, objects: list[dict], anchor: int, picked: list[int], folder: Path) -> Path:
    """The scene, twice as big, each object boxed with its id; the anchor black, the picked orange."""
    with Image.open(scene_path(scene)) as image:
        image = image.convert("RGB").resize((image.width * SCALE, image.height * SCALE), Image.NEAREST)
    pen = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=22)
    for item in objects:
        half = item["width"] * SCALE // 2 + 6
        x, y = item["x"] * SCALE, item["y"] * SCALE
        color = (0, 0, 0) if item["id"] == anchor else (255, 140, 0) if item["id"] in picked else GRAY_BOX
        pen.rectangle((x - half, y - half, x + half, y + half), outline=color, width=2 if color == GRAY_BOX else 4)
        pen.text((x - half, y - half - 26), str(item["id"]), fill=color, font=font)
    path = folder / f"{scene}.png"
    image.save(path)
    return path


def show_objects(objects: list[dict]) -> None:
    print(f"  {DIM}detect_objects found:{RESET}")
    for o in objects:
        print(f"    {o['id']:>2}  {o['size']:<5} {o['color']:<6} {o['shape']:<8}  x={o['x']:<3} y={o['y']}")


def judge(question: dict, key: dict, label: str, objects: list[int], reply: str) -> None:
    submitted = {"scene": question["scene"], "objects": objects, "answer": reply}
    verdict = verifier.verify_task(
        "scene-question",
        build_output(question, QuestionInput),
        build_output(submitted, AnswerOutput),
        build_output(key, AnswerKeyOutput),
        ".",
    )
    head = f"{GREEN}VALID{RESET}" if verdict["valid"] else f"{RED}INVALID{RESET}"
    print(f"\n  {BOLD}Submission — {label}:{RESET} objects={objects} answer={reply!r}")
    print(f"    {head}  score {verdict['score']:.2f}  {DIM}{verdict['message']}{RESET}")
    print("    " + "  ".join(f"{MARKS[c['ok']]} {c['id']}" for c in verdict["details"]["constraints"]))


def main() -> None:
    folder = Path(tempfile.mkdtemp(prefix="shape-scene-qa-demo-"))
    for number, (title, question, submissions) in enumerate(DEMOS, 1):
        print(f"\n{BOLD}━━━ {number}. {title} ━━━{RESET}")
        scene = plain_output(detect_objects(SceneInput(scene=question["scene"]), folder))
        show_objects(scene["objects"])
        try:
            key = plain_output(answer_key(build_output(question, QuestionInput), folder))
        except ValueError as error:
            print(f"\n  {BOLD}Question{RESET} on {question['scene']}: {words(question)}")
            print(f"  {RED}answer_key refuses it:{RESET} {error}")
            path = picture(question["scene"], scene["objects"], 0, [], folder)
        else:
            print(f"\n  {BOLD}Question{RESET} on {question['scene']}: {key['question']}")
            print(f"  {ORANGE}Answer key:{RESET} answer {key['answer']!r}, objects {key['objects']}, anchor {key['anchor']}")
            path = picture(question["scene"], scene["objects"], key["anchor"], key["objects"], folder)
            for label, objects, reply in submissions or [("a right answer", key["objects"], key["answer"])]:
                judge(question, key, label, objects, reply)
        print(f"\n  {DIM}picture: {path}{RESET}")
        Image.open(path).show()
    print(f"\n{DIM}Black box: the anchor. Orange: the objects the question picks out. Pictures in {folder}{RESET}\n")


if __name__ == "__main__":
    main()
