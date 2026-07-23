"""Component T — Tool Use (tool definitions + calling syntax). CCI §3.1
reconstruction, textual protocol only (§4.2.2). Benchmark-family specific:
the T block IS the tool definitions; without T no tools exist and only the
final `Answer:` line is valid output.

FREEZE RULE: post Phase-2 sign-off, edits = new template_id.
"""

NAME = "T"

_QA_SYNTAX = (
    "Emit exactly ONE action per message, alone on its own line, in exactly "
    "this form:\n"
    "Action: Search[entity or question]\n"
    "Action: Lookup[keyword]\n"
    "After each action you will receive an Observation with the result."
)

_MATH_SYNTAX = (
    "Emit exactly ONE action per message, alone on its own line, in exactly "
    "this form:\n"
    "Action: Calculate[arithmetic expression]\n"
    "After each action you will receive an Observation with the result."
)

TEMPLATES = {
    "qa": {
        "t1": (
            "Tools: You have two tools over the task's document collection.\n"
            "Search[q] returns the paragraph whose title best matches q, or "
            "similar titles if there is no match.\n"
            "Lookup[k] returns the next sentence containing k in the paragraph "
            "you most recently searched.\n" + _QA_SYNTAX
        ),
        "t2": (
            "Tools: Two tools are available on the shipped documents.\n"
            "Search[q] fetches the paragraph with the closest-matching title "
            "to q (or lists similar titles when nothing matches).\n"
            "Lookup[k] steps through sentences that mention k inside the most "
            "recently retrieved paragraph.\n" + _QA_SYNTAX
        ),
        "t3": (
            "Tools: You may query the provided document set with two tools.\n"
            "Search[q] looks up the paragraph titled most similarly to q and "
            "returns it (or suggests similar titles on a miss).\n"
            "Lookup[k] returns, one at a time, the sentences of the last "
            "searched paragraph that contain k.\n" + _QA_SYNTAX
        ),
    },
    "math": {
        "t1": (
            "Tools: You have one tool.\n"
            "Calculate[e] evaluates the arithmetic expression e (numbers, "
            "+ - * / ** parentheses, sqrt, common functions) and returns the "
            "value.\n" + _MATH_SYNTAX
        ),
        "t2": (
            "Tools: A single tool is available.\n"
            "Calculate[e] computes the numeric value of the expression e — "
            "basic arithmetic, powers, parentheses, sqrt and standard "
            "functions are supported.\n" + _MATH_SYNTAX
        ),
        "t3": (
            "Tools: One tool may be used.\n"
            "Calculate[e] returns the evaluated result of the arithmetic "
            "expression e (supports + - * / **, parentheses, sqrt, and common "
            "math functions).\n" + _MATH_SYNTAX
        ),
    },
}
