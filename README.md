# Shape Scene QA

A `nanoagent.plugin/v0001` plugin: visual question answering for a text-only
agent. Each of 40 bundled pictures holds colored squares, circles and
triangles. The agent cannot see pixels, so its one tool, a deterministic
detector, reads the picture and lists the objects; the agent reasons over that
list to answer a question such as "how many red objects are left of the large
blue square?". The verifier knows how each picture was drawn and checks both
the answer and the objects it rests on.

## Tools

| Tool | Does | Code |
|---|---|---|
| `detect_objects` | Finds every object in a scene's PNG from its pixels: each 4-connected region of one palette color, its size from its box (25 or 51 px), its shape from how much of the box it fills, its center, and an id in reading order | `src/plugin/detect.py` |
| `answer_key` | The answer key: answers the question from `detect_objects`'s objects by the rules in `questions.py`, and refuses a question with no one answer | `src/plugin/answer.py`, `src/plugin/questions.py` |

### Tasks

| Task | Does | Runner |
|---|---|---|
| `scene-question` | Answers a question about a scene and names the objects the answer rests on | `agent`, with `detect_objects`; reference `answer_key` |
| `detect-objects` | Lists the objects in a scene's picture | `tool` (`detect_objects`) |

## The task

A question is typed (`contract.QuestionInput`), never free text:

- `scene`: `scene-01` to `scene-40`.
- `ask`: `count`, `exists`, `color`, `shape` or `size`.
- `target`: a filter of color, shape and size, each possibly `any`.
- `relation`: `anywhere`, `left_of`, `right_of`, `above`, `below` or `nearest_to`.
- `anchor`: a filter that must match exactly one object (all `any` with `anywhere`).

The agent submits `scene`, `objects` (the ids the question picks out) and
`answer` (`"3"`, `"yes"`, `"red"`, ...). The rules, in `questions.py`:
targets never include the anchor; relations compare centers strictly, so an
object on the anchor's line is neither left nor right of it; `nearest_to` is
the least squared distance between centers. A question with no one answer is
refused by `answer_key` before any agent runs: an anchor that matches 0 or
several objects, a `color`/`shape`/`size` ask that picks out 0 or several
objects, or a tie for nearest.

## Ground truth

`src/plugin/tools_dev/make_scenes.py` draws every scene from fixed seeds
(scenes 01 to 36) or by hand (37 to 40, the boundary scenes) and writes the
objects it drew to `verifier/scenes.py`. It refuses to write anything unless
`detect_objects` finds exactly the drawn objects in every image, and the tests
check that again. The verifier never reads an image and never trusts a tool:
it re-derives every answer from its own copy of the drawn objects.

| Scene | Boundary it tests |
|---|---|
| `scene-37` | One object: no other can be an anchor, counts are 0 or 1 |
| `scene-38` | Three objects on the line x = 200: neither left nor right of each other |
| `scene-39` | Three objects 100 px from the gray square: `nearest_to` it is refused |
| `scene-40` | Four objects on the line y = 120, and two blue squares 2 px apart that must be told apart |

## Constraints

`verifier/task.py` judges a `scene-question` submission against 8
constraints, in order. Each entry of `details.constraints` is
`{id, constraint, ok, expected, actual, message}`; `ok` is `null` when a
constraint it needs did not hold.

| # | id | What it checks |
|---|---|---|
| 1 | `question` | The question is well formed and its scene exists |
| 2 | `well-posed` | The question has one answer on its scene |
| 3 | `answer-key` | The answer key pinned the answer the scene's true objects give |
| 4 | `same-scene` | The submission is for the question's scene |
| 5 | `answer-form` | The answer has the form its ask needs (`"3"`, not `"three"` or `"03"`; `"yes"`, not `"Yes"`) |
| 6 | `objects-known` | The submitted ids are the scene's, each once |
| 7 | `objects-exact` | The submitted ids are exactly those the question picks out |
| 8 | `answer-exact` | The answer is right |

Valid only when all 8 hold, with score 1.0. Any failure of 1 to 6 scores 0.
Otherwise the score is half the F1 of the submitted ids and half the answer,
at most 0.99. Each tool call is checked too: `detect_objects`'s output must be
exactly the scene's drawn objects, and `answer_key`'s must be the answer they
give.

## Limitations

- **The agent never sees pixels.** It tests reasoning over a perceived scene, not perception; the detector does the seeing, and works only on these flat, unshaded synthetic pictures.
- **A fixed set of 40 scenes.** An agent could in principle memorize them; new seeds make new scenes.
- **Did the agent look?** The verdict checks the answer and its objects, not that the agent called `detect_objects`; naming the exact objects by luck is unlikely, not impossible.

## Layout

```text
.
├── nanoagent.yaml   # manifest: id, runtime, permissions (no network), tools, tasks and the agent's instructions
├── contract.py      # each tool's and task's typed input and output: slimconfig Output classes
├── README.md
├── LICENSE
├── pyproject.toml   # pillow reads the scenes' PNGs
├── uv.lock
├── .gitignore
├── .env             # needed environment variable names (none here)
├── src/plugin/      # the MCP server (__main__.py), detect.py, answer.py, questions.py,
│                    #   scenes/ (the 40 PNGs) and tools_dev/make_scenes.py (draws them)
├── tests/           # the detector, the rules, the verifier and a scripted agent over every scene
├── ui/              # outputs drawn from their JSON Schema
├── product/         # the product page a catalog shows: product.yaml and icon.svg
└── verifier/        # deterministic verifier: scenes.py (the truth), questions.py (a copy of the rules),
                     #   one module per tool, and task.py for scene-question
```

## Develop and run

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run python -m plugin.tools_dev.make_scenes   # redraws the scenes; the same files each time
```

NanoAgent passes the folder the plugin may write to as `NANOAGENT_WORKSPACE`;
this plugin writes nothing there.
