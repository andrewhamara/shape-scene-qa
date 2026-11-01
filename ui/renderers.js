// How this plugin's page draws its tasks' outputs: the scene's picture (ui/scenes/), each object
// boxed on it with its id. A scene-question answer boxes the objects it submitted, the anchor and,
// when the check failed, the objects it missed; then states the question, the answer and the
// verdict's checks.
import { h, plural } from "./kit/components.js";
import { HEIGHT, SCENES, SIDES, WIDTH } from "./scenes.js";

const percent = (value, whole) => `${((value / whole) * 100).toFixed(3)}%`;

/** One object's box on the picture, placed in percent so it scales with the picture. */
function box({ id, x, y, size }, tone) {
  const half = SIDES[size] / 2 + 4;
  const place = [
    `--left: ${percent(x - half, WIDTH)}`,
    `--top: ${percent(y - half, HEIGHT)}`,
    `--side-x: ${percent(2 * half, WIDTH)}`,
    `--side-y: ${percent(2 * half, HEIGHT)}`,
  ].join("; ");
  // An id label over a box at the picture's top edge would be cut off: it goes inside the box.
  const edge = y - half < 16 ? " edge" : "";
  return h("div", { class: `scene-box ${tone}${edge}`, style: place }, h("span", { class: "scene-id", text: String(id) }));
}

/** The scene's picture with `boxes` over it. */
const picture = (scene, boxes) =>
  h(
    "div",
    { class: "scene-frame" },
    h("img", { class: "scene-img", src: `scenes/${scene}.png`, alt: `The picture of ${scene}`, width: WIDTH, height: HEIGHT }),
    boxes,
  );

const legend = (items) =>
  h(
    "p",
    { class: "scene-legend muted" },
    items.map(([tone, text]) => h("span", { class: "scene-key" }, h("span", { class: `scene-swatch ${tone}` }), text)),
  );

const describe = (o) => `${o.size} ${o.color} ${o.shape}`;

const MARKS = { true: ["✓", "ok"], false: ["✗", "bad"], null: ["·", "skipped"] };

/** The verdict's checks, each with its mark and, when it failed or was skipped, why. */
const checks = (constraints) =>
  h(
    "ol",
    { class: "scene-checks" },
    constraints.map(({ id, constraint, ok, message }) => {
      const [mark, tone] = MARKS[String(ok)];
      return h(
        "li",
        { class: `scene-check ${tone}` },
        h("span", { class: "scene-mark", text: mark }),
        h("span", {}, h("code", { text: id }), ` ${constraint}`, message ? h("span", { class: "scene-why", text: message }) : null),
      );
    }),
  );

export default {
  SceneOutput: ({ scene, objects }) =>
    h(
      "div",
      { class: "scene-card" },
      h("p", { class: "scene-title" }, h("strong", { text: scene }), ` · ${plural(objects.length, "object")}`),
      picture(scene, objects.map((o) => box(o, "plain"))),
      h(
        "ol",
        { class: "scene-list" },
        objects.map((o) => h("li", {}, h("strong", { text: `${o.id}` }), ` ${describe(o)} `, h("span", { class: "muted", text: `at x ${o.x}, y ${o.y}` }))),
      ),
    ),
  AnswerOutput: ({ scene, objects, answer }, { verdict }) => {
    const known = SCENES[scene] || [];
    const expected = (verdict.details && verdict.details.expected) || null;
    const anchor = expected ? expected.anchor : 0;
    const missed = expected && !verdict.valid ? expected.objects.filter((id) => !objects.includes(id)) : [];
    const tone = (o) =>
      o.id === anchor ? "anchor" : objects.includes(o.id) ? "picked" : missed.includes(o.id) ? "missed" : "plain";
    const keys = [["picked", "the agent's objects"]];
    if (anchor) keys.push(["anchor", "the anchor"]);
    if (missed.length) keys.push(["missed", "objects it missed"]);
    return h(
      "div",
      { class: "scene-card" },
      verdict.details && verdict.details.question ? h("p", { class: "scene-question", text: verdict.details.question }) : null,
      h(
        "p",
        { class: "scene-answer" },
        h("span", { class: "muted", text: "Answer " }),
        h("strong", { text: answer }),
        h("span", { class: "muted", text: objects.length ? ` · objects ${objects.join(", ")}` : " · no objects" }),
      ),
      known.length ? picture(scene, known.map((o) => box(o, tone(o)))) : h("p", { class: "muted", text: `No picture for ${scene}.` }),
      legend(keys),
      verdict.details && verdict.details.constraints ? checks(verdict.details.constraints) : null,
    );
  },
};
