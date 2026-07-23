"""Component M — Memory (structured scratchpad of confirmed facts / searched
entities / gaps). CCI §3.1 reconstruction. Prompt-only: the model maintains
the scratchpad in its own messages; the engine adds no state.

FREEZE RULE: post Phase-2 sign-off, edits = new template_id.
"""

NAME = "M"

TEMPLATES = {
    "t1": (
        "Memory: Maintain a scratchpad at the top of every message with three "
        "labeled sections — FACTS: facts you have confirmed so far; SEARCHED: "
        "entities and queries you have already tried; GAPS: what is still "
        "unknown. Update all three sections every step and rely on the "
        "scratchpad rather than re-reading earlier messages."
    ),
    "t2": (
        "Memory: Begin each message with an updated scratchpad containing "
        "FACTS (what you have established), SEARCHED (entities/queries already "
        "attempted), and GAPS (what remains missing). Keep it current at every "
        "step and consult it instead of scanning the earlier conversation."
    ),
    "t3": (
        "Memory: Every message must start with a three-part scratchpad — "
        "FACTS listing confirmed findings, SEARCHED listing entities and "
        "queries used so far, GAPS listing open unknowns. Refresh it each "
        "step and treat it, not the prior transcript, as your working memory."
    ),
}
