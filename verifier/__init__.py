"""The deterministic verifier: each tool's checks live in its own module, on contract instances.

It holds its own ground truth, verifier/scenes.py: the objects each scene was drawn with.
"""

from contract import Task, Tool

from . import answer, detect, task

TOOLS = {
    Tool.DETECT_OBJECTS: detect,
    Tool.ANSWER_KEY: answer,
}


def _tool_output(module):
    """A tool task's check: its output judged as its one tool's verify_output judges it."""
    return lambda arguments, output, reference, workspace: module.verify_output(arguments, output, workspace)


# task -> its output's check, verify_task(arguments, output, reference, workspace)
TASKS = {
    Task.SCENE_QUESTION: task.verify_task,
    Task.DETECT_OBJECTS: _tool_output(detect),
}


def verify_input(tool, value):
    return TOOLS[Tool(tool)].verify_input(value)


def verify_output(tool, input_value, output_value, workspace):
    return TOOLS[Tool(tool)].verify_output(input_value, output_value, workspace)


def verify_task(task, arguments, output, reference, workspace):
    return TASKS[Task(task)](arguments, output, reference, workspace)
