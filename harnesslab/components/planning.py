"""Component P — Planning (decompose into sub-goals). CCI §3.1 reconstruction.

FREEZE RULE: after Phase-2 sign-off these strings are immutable; any edit is a
new template_id. Content hashes of the rendered blocks go into every manifest.
"""

NAME = "P"

TEMPLATES = {
    "t1": (
        "Planning: Before doing anything else, decompose the problem into an "
        "explicit numbered plan of sub-goals, in the order you will resolve "
        "them. State the plan in your first message. When new information "
        "invalidates the plan, restate the updated plan before continuing."
    ),
    "t2": (
        "Planning: Start by breaking the task into a short numbered list of "
        "sub-goals arranged in the order you intend to tackle them, and write "
        "this plan out before your first step. If later findings make the "
        "plan obsolete, write out a corrected plan before you proceed."
    ),
    "t3": (
        "Planning: Your first message must lay out a numbered plan that splits "
        "the problem into ordered sub-goals. Follow the plan step by step, and "
        "whenever evidence contradicts it, revise the plan explicitly before "
        "taking the next step."
    ),
}
