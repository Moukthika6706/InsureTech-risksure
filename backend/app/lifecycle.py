"""Quote lifecycle: the only place a quote's status changes.

    draft ──rate──► quoted ──bind──► bound ──issue──► issued
      │               ▲
      ├──rate──► referred ──approve──┘
      │               └──decline──► declined
      └──rate──► declined

Every change writes an AuditEvent in the same transaction, so the audit
trail can never disagree with the quote.
"""
from sqlalchemy.orm import Session

from app.models import AuditEvent, Quote

# action -> {from_status: to_status}
TRANSITIONS = {
    "create":  {None: "draft"},
    "rate":    {"draft": None},           # target depends on the decision (see RATE_TARGET)
    "approve": {"referred": "quoted"},
    "decline": {"referred": "declined"},
    "bind":    {"quoted": "bound"},
    "issue":   {"bound": "issued"},
}
RATE_TARGET = {"auto_approve": "quoted", "approve_adjusted": "quoted",
               "refer": "referred", "decline": "declined"}
STATUSES = ["draft", "quoted", "referred", "declined", "bound", "issued"]


class InvalidTransition(Exception):
    """Raised when an action isn't allowed from the quote's current status (HTTP 409)."""


def transition(db: Session, quote: Quote, action: str, actor: str, detail: dict = None,
               decision: str = None) -> AuditEvent:
    allowed = TRANSITIONS.get(action)
    if allowed is None:
        raise ValueError(f"unknown action '{action}'")
    current = quote.status if quote.id else None
    if current not in allowed:
        raise InvalidTransition(
            f"Cannot {action} a quote that is '{current}'. "
            f"'{action}' is only allowed from: {', '.join(str(s) for s in allowed)}.")
    target = RATE_TARGET[decision] if action == "rate" else allowed[current]

    quote.status = target
    event = AuditEvent(quote=quote, action=action, from_status=current, to_status=target,
                       actor=actor, detail=detail or {})
    db.add(event)
    return event
