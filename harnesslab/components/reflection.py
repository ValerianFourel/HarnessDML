"""Component R — Reflection (post-step self-check). CCI §3.1 reconstruction.

FREEZE RULE: post Phase-2 sign-off, edits = new template_id.
"""

NAME = "R"

TEMPLATES = {
    "t1": (
        "Reflection: After every observation, briefly check yourself before "
        "moving on: did the observation actually support your previous "
        "inference? If you detect an error, a contradiction, or a dead end, "
        "say so explicitly and correct course before the next step."
    ),
    "t2": (
        "Reflection: Once you receive each observation, pause to verify it: "
        "does it really back up what you inferred last step? On spotting a "
        "mistake, inconsistency, or dead end, state it openly and change "
        "course before proceeding."
    ),
    "t3": (
        "Reflection: Following every observation, run a short self-check — "
        "confirm the observation supports your latest inference. Whenever it "
        "does not, or you have hit a dead end, acknowledge it explicitly and "
        "adjust your approach before continuing."
    ),
}
