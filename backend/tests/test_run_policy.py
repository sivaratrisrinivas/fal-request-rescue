"""Execution-policy ordering as pure decisions. Routes adapt verdicts to HTTP."""
from app.run_policy import decide_run


def test_replay_always_allowed_without_gates():
    v = decide_run(mode="replay", pending_request_ids=[], key_present=False,
                   spent=999.0, session_cap=2.0, day_cap=5.0, cost=0.0,
                   approved=False, status_checked=False)
    assert v == {"allowed": True, "code": "OK", "message": "Replay needs no approval or spend."}


def test_pending_blocks_before_key_check():
    v = decide_run(mode="live", pending_request_ids=["r-1"], key_present=False,
                   spent=0.0, session_cap=2.0, day_cap=5.0, cost=0.01,
                   approved=False, status_checked=False)
    assert v["allowed"] is False and v["code"] == "CHECK_STATUS_FIRST"


def test_status_check_clears_pending_block():
    v = decide_run(mode="live", pending_request_ids=["r-1"], key_present=False,
                   spent=0.0, session_cap=2.0, day_cap=5.0, cost=0.01,
                   approved=False, status_checked=True)
    assert v["code"] == "LIVE_UNAVAILABLE"


def test_missing_key_blocks_before_spend():
    v = decide_run(mode="live", pending_request_ids=[], key_present=False,
                   spent=0.0, session_cap=2.0, day_cap=5.0, cost=0.01,
                   approved=True, status_checked=True)
    assert v["allowed"] is False and v["code"] == "LIVE_UNAVAILABLE"


def test_caps_block_before_approval():
    v = decide_run(mode="live", pending_request_ids=[], key_present=True,
                   spent=0.0, session_cap=2.0, day_cap=5.0, cost=500.0,
                   approved=False, status_checked=True)
    assert v["allowed"] is False and v["code"] == "SPEND_BLOCKED"


def test_approval_required_after_caps_pass():
    v = decide_run(mode="live", pending_request_ids=[], key_present=True,
                   spent=0.0, session_cap=2.0, day_cap=5.0, cost=0.01,
                   approved=False, status_checked=True)
    assert v["allowed"] is False and v["code"] == "APPROVAL_REQUIRED"


def test_fully_gated_run_allowed():
    v = decide_run(mode="live", pending_request_ids=[], key_present=True,
                   spent=0.0, session_cap=2.0, day_cap=5.0, cost=0.01,
                   approved=True, status_checked=True)
    assert v["allowed"] is True and v["code"] == "OK"
