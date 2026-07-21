"""
Compliance audit trail helper.

Every create/update/delete on a tracked entity (currently: tickets, users)
writes one AuditLog row recording who did it, what changed, and when.
Audit rows are append-only -- nothing here ever updates or deletes one.
"""
import json
import enum
from datetime import datetime
from typing import Optional, Any

from sqlalchemy.orm import Session

import models


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, enum.Enum):
        return value.value
    return value


def snapshot(instance, fields: list[str]) -> dict:
    """Takes a plain-dict snapshot of the given fields on a model instance."""
    return {field: _json_safe(getattr(instance, field, None)) for field in fields}


def record_audit(
    db: Session,
    actor: Optional["models.User"],
    entity_type: str,
    entity_id: int,
    action: str,
    old_values: Optional[dict] = None,
    new_values: Optional[dict] = None,
) -> models.AuditLog:
    log = models.AuditLog(
        actor_id=actor.id if actor else None,
        actor_role=actor.role.value if actor else None,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_values=json.dumps(old_values) if old_values is not None else None,
        new_values=json.dumps(new_values) if new_values is not None else None,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
