"""A scene question's rules: which objects it picks out, and its one answer.

src/plugin/questions.py and verifier/questions.py are byte-for-byte copies (a test enforces it):
the answer key and the verifier answer by the same rules. Pure standard library, on plain values:
an object is a dict with id, shape, color, size, x and y; a question is a dict with ask, target,
relation and anchor, each filter a dict of color, shape and size, any value "any".
"""

ANY = "any"
KEYS = ("size", "color", "shape")
# relation -> whether an object at (x, y) is placed so relative to an anchor at (ax, ay)
PLACED = {
    "left_of": lambda x, y, ax, ay: x < ax,
    "right_of": lambda x, y, ax, ay: x > ax,
    "above": lambda x, y, ax, ay: y < ay,
    "below": lambda x, y, ax, ay: y > ay,
}
PHRASES = {
    "anywhere": "in the scene",
    "left_of": "left of",
    "right_of": "right of",
    "above": "above",
    "below": "below",
    "nearest_to": "nearest to",
}


class IllPosed(ValueError):
    """The question has no one answer on this scene."""


def matches(item, wanted):
    return all(wanted[key] in (ANY, item[key]) for key in KEYS)


def describe(wanted, plural=False):
    """A filter in words, e.g. "large blue squares" or "objects"."""
    words = [wanted[key] for key in ("size", "color") if wanted[key] != ANY]
    noun = "object" if wanted["shape"] == ANY else wanted["shape"]
    return " ".join([*words, noun + ("s" if plural else "")])


def anchor_problem(question):
    """What is wrong with the question's anchor whatever the scene, or None."""
    bare = all(question["anchor"][key] == ANY for key in KEYS)
    if question["relation"] == "anywhere" and not bare:
        return "with relation anywhere the anchor must be all any"
    if question["relation"] != "anywhere" and bare:
        return f"with relation {question['relation']} the anchor must name its color, shape or size"
    return None


def words(question):
    """The question in words."""
    ask, relation = question["ask"], question["relation"]
    where = PHRASES[relation]
    if relation != "anywhere":
        where = f"{where} the {describe(question['anchor'])}"
    if ask == "count":
        return f"How many {describe(question['target'], plural=True)} are {where}?"
    if ask == "exists":
        return f"Is there a {describe(question['target'])} {where}?"
    return f"What {ask} is the {describe(question['target'])} {where}?"


def anchor_of(objects, question):
    """The anchor object, or None when the relation is anywhere; IllPosed unless exactly one object matches it."""
    if question["relation"] == "anywhere":
        return None
    found = [item for item in objects if matches(item, question["anchor"])]
    if len(found) != 1:
        raise IllPosed(f"{len(found)} objects are {describe(question['anchor'])}s: the anchor must be exactly one")
    return found[0]


def picked(objects, question):
    """The anchor (or None) and the objects the question picks out, in id order."""
    anchor = anchor_of(objects, question)
    targets = [item for item in objects if matches(item, question["target"]) and item is not anchor]
    relation = question["relation"]
    if relation == "anywhere":
        return anchor, targets
    if relation in PLACED:
        place = PLACED[relation]
        return anchor, [item for item in targets if place(item["x"], item["y"], anchor["x"], anchor["y"])]
    if not targets:
        return anchor, []
    # nearest_to: the least squared distance between centers, which must be one object's alone.
    distance = {item["id"]: (item["x"] - anchor["x"]) ** 2 + (item["y"] - anchor["y"]) ** 2 for item in targets}
    least = min(distance.values())
    nearest = [item for item in targets if distance[item["id"]] == least]
    if len(nearest) > 1:
        ids = ", ".join(str(item["id"]) for item in nearest)
        raise IllPosed(f"objects {ids} are equally near the {describe(question['anchor'])}: no one is nearest")
    return anchor, nearest


def answer(objects, question):
    """(anchor id or 0, the picked ids ascending, the answer), or IllPosed."""
    anchor, found = picked(objects, question)
    ids = sorted(item["id"] for item in found)
    ask = question["ask"]
    if ask == "count":
        reply = str(len(found))
    elif ask == "exists":
        reply = "yes" if found else "no"
    else:
        if len(found) != 1:
            raise IllPosed(f"{len(found)} objects are picked out: asking their {ask} needs exactly one")
        reply = found[0][ask]
    return (anchor["id"] if anchor else 0), ids, reply


def answer_problem(ask, reply):
    """What is wrong with the form of ``reply`` for ``ask``, or None."""
    forms = {
        "exists": ("yes", "no"),
        "color": ("red", "green", "blue", "yellow", "purple", "gray"),
        "shape": ("square", "circle", "triangle"),
        "size": ("small", "large"),
    }
    if ask == "count":
        if not reply.isdigit() or not reply.isascii() or (len(reply) > 1 and reply[0] == "0"):
            return f"a count is a number in digits, such as 3, not {reply!r}"
        return None
    if reply not in forms[ask]:
        return f"a {ask} answer is one of {', '.join(forms[ask])}, not {reply!r}"
    return None
