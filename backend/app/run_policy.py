"""Execution policy: what may run, and in what gate order.

Pure decisions — no store, no network, no clock. Routes gather inputs, call
`decide_run`, then persist the outcome and adapt the verdict to HTTP.
Gate order is code law: pending-status → key → spend caps → approval.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Verdict:
    allowed: bool
    code: str
    message: str

    def as_dict(self) -> dict:
        return {"allowed": self.allowed, "code": self.code, "message": self.message}


def decide_run(*, mode: str, pending_request_ids: list, key_present: bool,
               spent: float, session_cap: float, day_cap: float, cost: float,
               approved: bool, status_checked: bool) -> dict:
    if mode == "replay":
        return Verdict(True, "OK", "Replay needs no approval or spend.").as_dict()
    if pending_request_ids and not status_checked:
        ids = ", ".join(pending_request_ids)
        return Verdict(False, "CHECK_STATUS_FIRST",
                       f"Request(s) {ids} still pending — check status before a new run.").as_dict()
    if not key_present:
        return Verdict(False, "LIVE_UNAVAILABLE",
                       "No live runner configured server-side.").as_dict()
    if spent + cost > session_cap or spent + cost > day_cap:
        return Verdict(False, "SPEND_BLOCKED",
                       f"Cost {cost} exceeds caps (session {session_cap}, day {day_cap}).").as_dict()
    if not approved:
        return Verdict(False, "APPROVAL_REQUIRED",
                       "Analyst approval required before any paid run.").as_dict()
    return Verdict(True, "OK", "All gates passed.").as_dict()
