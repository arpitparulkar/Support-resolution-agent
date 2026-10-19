"""Small, independently testable tools for order and support operations."""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.tools import tool


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DATA_LOCK = threading.Lock()
_ORDER_ID_PATTERN = re.compile(r"^ORD\d{3,}$", re.IGNORECASE)


def _data_path(filename: str) -> Path:
    """Resolve data from the project folder or an isolated test data directory."""
    configured_dir = os.getenv("SUPPORT_AGENT_DATA_DIR")
    data_dir = Path(configured_dir) if configured_dir else _PROJECT_ROOT / "data"
    return data_dir / filename


def _error(code: str, message: str) -> dict[str, Any]:
    """Return a consistent, JSON-serializable tool error."""
    return {"ok": False, "error": {"code": code, "message": message}}


def _load_json(filename: str) -> list[dict[str, Any]]:
    """Load one JSON data file and reject malformed top-level data."""
    path = _data_path(filename)
    with path.open("r", encoding="utf-8") as data_file:
        value = json.load(data_file)
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ValueError(f"{filename} must contain a JSON array of objects.")
    return value


def _save_json(filename: str, value: list[dict[str, Any]]) -> None:
    """Atomically replace a JSON data file to avoid partial writes."""
    path = _data_path(filename)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8", newline="\n") as data_file:
        json.dump(value, data_file, indent=2, ensure_ascii=False)
        data_file.write("\n")
    temporary_path.replace(path)


def _get_order(order_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Validate and retrieve an order, returning a structured error if absent."""
    if not isinstance(order_id, str) or not _ORDER_ID_PATTERN.fullmatch(order_id.strip()):
        return None, _error("invalid_order_id", "Provide a valid order ID such as ORD123.")
    try:
        orders = _load_json("orders.json")
    except FileNotFoundError:
        return None, _error("data_file_missing", "The order data file is unavailable.")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return None, _error("data_file_invalid", f"Order data could not be read: {exc}")

    normalized_id = order_id.strip().upper()
    for order in orders:
        if str(order.get("order_id", "")).upper() == normalized_id:
            return order, None
    return None, _error("order_not_found", f"No order was found for {normalized_id}.")


def _verify_customer(order: dict[str, Any], customer_name: str) -> dict[str, Any] | None:
    """Require an exact case-insensitive customer-name match for sensitive actions."""
    if not isinstance(customer_name, str) or not customer_name.strip():
        return _error("verification_required", "Ask the customer for the name on the order.")
    expected = str(order.get("customer", "")).strip().casefold()
    supplied = customer_name.strip().casefold()
    if not expected or expected != supplied:
        return _error("verification_failed", "The name does not match this order. No changes were made.")
    return None


def _refund_eligibility(order: dict[str, Any], reason: str) -> dict[str, Any]:
    """Apply refund policy without exposing customer-only fields."""
    if not isinstance(reason, str) or not reason.strip():
        return _error("invalid_reason", "A refund reason is required.")
    if str(order.get("refund_status", "")).casefold() == "refunded":
        return {"ok": True, "eligible": False, "reason": "This order has already been refunded."}
    if str(order.get("status", "")).casefold() != "delivered":
        return {"ok": True, "eligible": False, "reason": "A refund under this policy requires a delivered order."}

    normalized_reason = reason.casefold()
    if not any(term in normalized_reason for term in ("damaged", "damage", "defective", "defect")):
        return {"ok": True, "eligible": False, "reason": "This policy covers damaged or defective items only."}

    delivered_date = order.get("delivered_date")
    try:
        days_since_delivery = (date.today() - date.fromisoformat(str(delivered_date))).days
    except (TypeError, ValueError):
        return _error("invalid_order_data", "The delivery date is missing or invalid.")
    if days_since_delivery < 0 or days_since_delivery > 30:
        return {
            "ok": True,
            "eligible": False,
            "reason": "The 30-day return window has expired or the delivery date is in the future.",
        }
    return {"ok": True, "eligible": True, "reason": "The item is within the 30-day damaged-item policy."}


@tool
def get_order_status(order_id: str) -> dict[str, Any]:
    """Look up an order's status and delivery dates using its order ID."""
    order, failure = _get_order(order_id)
    if failure:
        return failure
    assert order is not None
    return {
        "ok": True,
        "order": {
            "order_id": order.get("order_id"),
            "product": order.get("product"),
            "status": order.get("status"),
            "expected_delivery": order.get("expected_delivery"),
            "delivered_date": order.get("delivered_date"),
            "refund_status": order.get("refund_status"),
        },
    }


@tool
def lookup_policy(topic: str) -> dict[str, Any]:
    """Read the matching refund, cancellation, delivery, payment, or general policy."""
    if not isinstance(topic, str) or not topic.strip():
        return _error("invalid_topic", "Provide a policy topic to look up.")
    path = _data_path("policies.txt")
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return _error("data_file_missing", "The policy file is unavailable.")
    except OSError as exc:
        return _error("data_file_unreadable", f"The policy file could not be read: {exc}")

    topic_words = set(re.findall(r"[a-z]+", topic.casefold()))
    aliases = {
        "REFUNDS": {"refund", "refunded", "refunds", "damaged", "defective"},
        "CANCELLATIONS": {"cancel", "cancellation", "cancelled", "canceled"},
        "DELIVERY": {"delivery", "delayed", "late", "shipping", "arrive"},
        "PAYMENTS": {"payment", "charged", "duplicate", "billing"},
        "GENERAL": {"general", "policy", "other"},
    }
    selected = next((section for section, words in aliases.items() if topic_words & words), "GENERAL")
    sections: dict[str, list[str]] = {}
    current_section = ""
    for line in text.splitlines():
        heading = line.strip()
        if heading and heading.isupper():
            current_section = heading
            sections[current_section] = []
        elif current_section:
            sections[current_section].append(line)
    policy = "\n".join(sections.get(selected, [])).strip()
    if not policy:
        return _error("policy_not_found", "No matching policy section is available.")
    return {"ok": True, "topic": selected.casefold(), "policy": policy}


@tool
def check_refund_eligibility(order_id: str, reason: str, customer_name: str) -> dict[str, Any]:
    """Verify the customer and check the 30-day damaged-item refund policy."""
    order, failure = _get_order(order_id)
    if failure:
        return failure
    assert order is not None
    verification_error = _verify_customer(order, customer_name)
    if verification_error:
        return verification_error
    return _refund_eligibility(order, reason)


@tool
def request_refund(order_id: str, reason: str, customer_name: str) -> dict[str, Any]:
    """Issue a simulated refund only after customer verification and eligibility checks."""
    if not isinstance(reason, str) or not reason.strip():
        return _error("invalid_reason", "A refund reason is required.")
    with _DATA_LOCK:
        order, failure = _get_order(order_id)
        if failure:
            return failure
        assert order is not None
        verification_error = _verify_customer(order, customer_name)
        if verification_error:
            return verification_error
        eligibility = _refund_eligibility(order, reason)
        if not eligibility.get("ok") or not eligibility.get("eligible"):
            return eligibility
        try:
            orders = _load_json("orders.json")
            for item in orders:
                if str(item.get("order_id", "")).upper() == str(order_id).strip().upper():
                    item["refund_status"] = "Refunded"
                    break
            _save_json("orders.json", orders)
        except FileNotFoundError:
            return _error("data_file_missing", "The order data file is unavailable.")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            return _error("data_write_failed", f"The refund was not recorded: {exc}")

    return {
        "ok": True,
        "confirmation_id": f"RFND-{uuid.uuid4().hex[:10].upper()}",
        "status": "Refunded",
        "message": "The simulated refund was successfully recorded.",
    }


@tool
def cancel_order(order_id: str, customer_name: str) -> dict[str, Any]:
    """Cancel an unshipped order after verifying the name on the order."""
    with _DATA_LOCK:
        order, failure = _get_order(order_id)
        if failure:
            return failure
        assert order is not None
        verification_error = _verify_customer(order, customer_name)
        if verification_error:
            return verification_error
        if str(order.get("status", "")).casefold() != "processing":
            return {
                "ok": True,
                "cancelled": False,
                "reason": "Only orders that have not shipped can be cancelled.",
            }
        try:
            orders = _load_json("orders.json")
            for item in orders:
                if str(item.get("order_id", "")).upper() == str(order_id).strip().upper():
                    item["status"] = "Cancelled"
                    break
            _save_json("orders.json", orders)
        except FileNotFoundError:
            return _error("data_file_missing", "The order data file is unavailable.")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            return _error("data_write_failed", f"The cancellation was not recorded: {exc}")
    return {"ok": True, "cancelled": True, "order_id": order_id.strip().upper()}


@tool
def create_support_ticket(issue: str, priority: str, order_id: str | None = None) -> dict[str, Any]:
    """Persist a support ticket with low, medium, or high priority."""
    if not isinstance(issue, str) or not issue.strip():
        return _error("invalid_issue", "Describe the issue before creating a ticket.")
    if not isinstance(priority, str) or priority.casefold() not in {"low", "medium", "high"}:
        return _error("invalid_priority", "Priority must be low, medium, or high.")
    normalized_order_id: str | None = None
    if order_id:
        order, failure = _get_order(order_id)
        if failure:
            return failure
        assert order is not None
        normalized_order_id = str(order.get("order_id", order_id)).upper()

    with _DATA_LOCK:
        try:
            tickets = _load_json("tickets.json")
            existing_numbers = [
                int(match.group(1))
                for ticket in tickets
                if (match := re.fullmatch(r"TKT(\d+)", str(ticket.get("ticket_id", ""))))
            ]
            ticket_number = max([100, *existing_numbers]) + 1
            ticket = {
                "ticket_id": f"TKT{ticket_number}",
                "issue": issue.strip(),
                "priority": priority.casefold(),
                "order_id": normalized_order_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "Open",
            }
            tickets.append(ticket)
            _save_json("tickets.json", tickets)
        except FileNotFoundError:
            return _error("data_file_missing", "The ticket data file is unavailable.")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            return _error("ticket_write_failed", f"The support ticket could not be saved: {exc}")
    return {"ok": True, "ticket_id": ticket["ticket_id"], "ticket": ticket}


SUPPORT_TOOLS = [
    get_order_status,
    lookup_policy,
    check_refund_eligibility,
    request_refund,
    cancel_order,
    create_support_ticket,
]
