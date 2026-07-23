"""Component SR — Structured Reasoning (per-step Evidence → Gap → Reasoning →
Next step). CCI §3.1 reconstruction.

FREEZE RULE: post Phase-2 sign-off, edits = new template_id.
"""

NAME = "SR"

TEMPLATES = {
    "t1": (
        "Structured reasoning: Structure the body of every step in exactly "
        "this format —\n"
        "Evidence: what you currently know that bears on the question.\n"
        "Gap: the specific piece of information still missing.\n"
        "Reasoning: the inference that connects the evidence to the gap.\n"
        "Next step: the single next action, or the final answer."
    ),
    "t2": (
        "Structured reasoning: Lay out each step using exactly these four "
        "labeled lines —\n"
        "Evidence: the relevant facts in hand.\n"
        "Gap: what is still unknown and needed.\n"
        "Reasoning: how the evidence points at closing the gap.\n"
        "Next step: the one action you will take next, or the final answer."
    ),
    "t3": (
        "Structured reasoning: Every step must follow this exact template —\n"
        "Evidence: what is established so far.\n"
        "Gap: the missing information blocking the answer.\n"
        "Reasoning: the argument from the evidence toward that gap.\n"
        "Next step: a single next action, or the final answer."
    ),
}
