"""Shape A — deterministic workflow. Student work.

Signature (do not change):

    run_claim(claim_id, *, seed, store_path, crash_at=None) -> RunResult

Money stays in code (`lab8.tools.compute_compensation`).
"""

from __future__ import annotations

import sqlite3

from lab8.db import connect
from lab8.durability import InjectedCrash, committed_audit_count, get_refund, issue_refund
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.tools import compute_compensation, get_claim_view, lookup_order, tool_cost
from lab8.trace import Trace


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    run_id = make_run_id("workflow", claim_id, seed)
    trace = Trace(run_id)
    budget = Budget()
    conn: sqlite3.Connection | None = None

    try:
        conn = connect(store_path)
        return _run(conn, claim_id, seed=seed, crash_at=crash_at, trace=trace, budget=budget)
    except InjectedCrash:
        # The host may already have committed the refund. Persist the trace and
        # let the harness observe the injected crash so it can resume the claim.
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise
    except Exception:
        # Keep unexpected implementation/database details out of the trace and
        # result; they could contain user data. The contract requires a result
        # instead of an exception for ordinary failures.
        trace.add("error", {"reason": "internal_error"})
        return _failed_result(conn, claim_id, seed, trace, budget)
    finally:
        if conn is not None:
            conn.close()


def _run(
    conn: sqlite3.Connection,
    claim_id: str,
    *,
    seed: int,
    crash_at: str | None,
    trace: Trace,
    budget: Budget,
) -> RunResult:
    budget.add_tool(tool_cost())
    claim = get_claim_view(conn, claim_id)
    trace.add(
        "claim_view",
        {"found": bool(claim.get("found")), "has_order_id": bool(claim.get("order_id"))},
    )
    if not claim.get("found"):
        trace.add("decision", {"status": "failed", "reason": "unknown_claim"})
        return finish(
            conn,
            shape="workflow",
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="unknown_claim",
        )

    if not claim.get("order_id"):
        trace.add("decision", {"status": "needs_info", "reason": "missing_order_id"})
        return finish(
            conn,
            shape="workflow",
            claim_id=claim_id,
            seed=seed,
            status="needs_info",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="missing_order_id",
        )

    budget.add_tool(tool_cost())
    order_view = lookup_order(conn, claim["order_id"], claim["principal_id"])
    trace.add("order_lookup", {"visible": bool(order_view.get("visible")), "reason": order_view.get("reason")})
    if not order_view.get("visible"):
        trace.add("decision", {"status": "escalated", "reason": order_view.get("reason")})
        return finish(
            conn,
            shape="workflow",
            claim_id=claim_id,
            seed=seed,
            status="escalated",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=order_view.get("reason"),
        )

    # lookup_order returns only its documented allowlist. In particular, the
    # raw claim ticket and private order columns never enter the trace.
    budget.add_tool(tool_cost())
    quote = compute_compensation(conn, order_view["order"])
    proposal = int(quote["amount_vnd"])
    trace.add(
        "quote",
        {
            "amount_vnd": proposal,
            "reason": quote.get("reason"),
            "clause_ids": quote.get("clause_ids", []),
            "parts": quote.get("parts", {}),
        },
    )

    if proposal <= 0:
        trace.add("decision", {"status": "denied", "reason": quote.get("reason")})
        return finish(
            conn,
            shape="workflow",
            claim_id=claim_id,
            seed=seed,
            status="denied",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=quote.get("reason"),
        )

    # Pass the full entitlement quote. The host enforces approval, idempotency,
    # and the remaining per-order cap inside its transaction.
    budget.add_tool(tool_cost())
    outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    trace.add("refund_request", {"ok": bool(outcome.get("ok")), "reason": outcome.get("reason")})
    if not outcome.get("ok"):
        status = "failed" if outcome.get("conflict") else "denied"
        trace.add("decision", {"status": status, "reason": outcome.get("reason")})
        return finish(
            conn,
            shape="workflow",
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=outcome.get("reason"),
        )

    trace.add("decision", {"status": "resolved"})
    return finish(
        conn,
        shape="workflow",
        claim_id=claim_id,
        seed=seed,
        status="resolved",
        proposal_amount=proposal,
        budget=budget,
        trace=trace,
    )


def _failed_result(
    conn: sqlite3.Connection | None,
    claim_id: str,
    seed: int,
    trace: Trace,
    budget: Budget,
) -> RunResult:
    """Build a safe failure result even when the store could not be read."""
    effect: dict | None = None
    audit_count = 0
    if conn is not None:
        try:
            effect = get_refund(conn, claim_id)
            audit_count = committed_audit_count(conn, claim_id)
        except sqlite3.Error:
            # A malformed or unavailable store cannot provide ledger evidence.
            pass

    trace_path = trace.write()
    return RunResult(
        run_id=trace.run_id,
        claim_id=claim_id,
        shape="workflow",
        seed=seed,
        status="failed",
        proposal_amount=0,
        refund_effects=[effect] if effect else [],
        committed_audit_count=audit_count,
        model_calls=budget.model_calls,
        tool_calls=budget.tool_calls,
        input_tokens=budget.input_tokens,
        output_tokens=budget.output_tokens,
        cost_estimate=round(budget.cost_estimate, 6),
        trace_path=trace_path,
        error_reason="internal_error",
    )
