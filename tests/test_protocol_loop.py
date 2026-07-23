"""§8.2 — action grammar, malformed actions, retry-once, `Answer:` edge cases,
and every finish_reason branch of the fixed loop (mock backend only)."""

import asyncio

import pytest

from harnesslab.agent.loop import build_messages, run_rollout
from harnesslab.client import MockClient, scripted
from harnesslab.protocol import parse_action, parse_answer, parse_confidence
from harnesslab.tools import DocStore, ToolBox

PARAS = [("Heidelberg", "Heidelberg is a city in Germany. It lies on the Neckar river.")]


def qa_toolbox() -> ToolBox:
    return ToolBox("qa", DocStore(PARAS))


def run(client, toolbox=qa_toolbox, **kw):
    defaults = dict(
        step_cap=4, max_new_tokens=256, temperature=0.1, top_p=0.9, seed=0,
        system_role_mode="native", timeout_s=60.0,
    )
    defaults.update(kw)
    return asyncio.run(
        run_rollout(client, "SYSTEM", "Where is Heidelberg?",
                    toolbox() if callable(toolbox) else toolbox, **defaults)
    )


# ── grammar ──────────────────────────────────────────────────────────────────
def test_action_grammar():
    assert parse_action("Action: Search[Paris]") == ("Search", "Paris")
    assert parse_action("thinking...\nAction: Lookup[river]\n") == ("Lookup", "river")
    assert parse_action("Action: Calculate[(1+2)*3]") == ("Calculate", "(1+2)*3")
    assert parse_action("Action: search[x]") is None          # case-sensitive
    assert parse_action("Action: Search[x") is None           # unclosed
    assert parse_action("Action: Finish[x]") is None          # unknown verb
    assert parse_action("Do the Action: thing") is None


def test_answer_edge_cases():
    assert parse_answer("Answer: 42") == "42"
    assert parse_answer("Answer: first\nblah\nAnswer: second") == "second"  # last wins
    assert parse_answer("Answer:   spaced   ") == "spaced"
    assert parse_answer("Answer:") is None                    # empty is not an answer
    assert parse_answer("answer: lowercase") is None
    assert parse_answer("The Answer: inline") is None         # line-anchored


def test_confidence_parsing():
    assert parse_confidence(" 87 ") == 87.0
    assert parse_confidence("87.5") == 87.0
    assert parse_confidence("101") is None
    assert parse_confidence("high") is None
    assert parse_confidence("") is None


# ── loop behavior ────────────────────────────────────────────────────────────
def test_happy_path_action_then_answer_then_confidence():
    tr = run(MockClient(scripted([
        "Action: Search[Heidelberg]", "Answer: Germany", "87",
    ])))
    assert tr.finish_reason == "answered" and tr.answer == "Germany"
    assert tr.n_tool_calls == 1 and tr.action_seq == ["S", "A"]
    assert tr.confidence == 87.0 and tr.confidence_source == "elicited"
    assert tr.n_turns == 3  # two protocol turns + confidence turn


def test_retry_once_then_recover():
    tr = run(MockClient(scripted(["Action: Serch[x]", "Answer: 42", "50"])))
    assert tr.finish_reason == "answered"
    assert tr.n_parse_failures == 1


def test_two_malformed_actions_is_parse_loop():
    tr = run(MockClient(scripted(["Action: Serch[x]", "Action: Serch[x]"])))
    assert tr.finish_reason == "parse_loop"
    assert tr.n_parse_failures == 2 and tr.answer is None


def test_two_prose_turns_is_no_answer():
    tr = run(MockClient(scripted(["I am thinking.", "Still thinking."])))
    assert tr.finish_reason == "no_answer"


def test_step_cap():
    tr = run(MockClient(scripted(["Action: Search[Heidelberg]"])), step_cap=3)
    assert tr.finish_reason == "step_cap"
    assert tr.n_tool_calls == 3 and tr.n_turns == 3


def test_answer_wins_when_both_present():
    tr = run(MockClient(scripted(["Action: Search[Heidelberg]\nAnswer: Germany", "90"])))
    assert tr.finish_reason == "answered" and tr.answer == "Germany"
    assert tr.n_tool_calls == 0


def test_action_without_tools_fails_to_parse_loop():
    tr = run(MockClient(scripted(["Action: Search[x]", "Action: Search[x]"])), toolbox=None)
    assert tr.finish_reason == "parse_loop"


def test_disallowed_verb_for_family_counts_as_failure():
    tr = run(MockClient(scripted(["Action: Calculate[1+1]", "Answer: 2", "10"])))
    assert tr.finish_reason == "answered"
    assert tr.n_parse_failures == 1 and tr.n_tool_calls == 0


def test_timeout():
    tr = run(MockClient(scripted(["Answer: 42"])), timeout_s=0.0)
    assert tr.finish_reason == "timeout" and tr.n_turns == 0


def test_api_error_terminal():
    tr = run(MockClient(scripted(["Answer: 42"]), fail_times=99))
    assert tr.finish_reason == "api_error"


def test_confidence_fallback_on_non_numeric():
    tr = run(MockClient(scripted(["Answer: 42", "quite sure"])))
    assert tr.answered and tr.confidence is None and tr.confidence_source == "fallback"


def test_confidence_can_be_disabled():
    tr = run(MockClient(scripted(["Answer: 42"])), elicit_confidence=False)
    assert tr.answered and tr.confidence_source is None and tr.n_turns == 1


def test_prepended_system_role_mode():
    msgs = build_messages("SYS", "Q?", "prepended")
    assert len(msgs) == 1 and msgs[0]["role"] == "user"
    assert msgs[0]["content"].startswith("SYS\n\nQ?"[:3])
    tr = run(MockClient(scripted(["Answer: ok", "70"])), system_role_mode="prepended")
    assert tr.answered


def test_bad_system_role_mode_rejected():
    with pytest.raises(ValueError):
        build_messages("s", "q", "weird")


def test_usage_accounting_accumulates():
    tr = run(MockClient(scripted(["Action: Search[Heidelberg]", "Answer: Germany", "80"])))
    assert tr.tokens_in > 0 and tr.tokens_out > 0
    assert tr.chars_out == len("Action: Search[Heidelberg]") + len("Answer: Germany") + len("80")
    assert len(tr.latencies_ms) == 3
