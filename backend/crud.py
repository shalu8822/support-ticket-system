"""
Data-access helpers. Routers call these instead of touching the ORM
directly, so query logic stays in one place and is easy to unit test.
"""
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import func, extract,Column
from sqlalchemy.orm import Session

import models
import schemas
from security import hash_password
import json


# --------------------------------------------------------------- Users -----
def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email.lower()).first()


def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, user_in: schemas.UserCreate, role: models.RoleEnum = models.RoleEnum.user) -> models.User:
    user = models.User(
        name=user_in.name,
        email=user_in.email.lower(),
        password=hash_password(user_in.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session, role: Optional[models.RoleEnum] = None):
    query = db.query(models.User)
    if role is not None:
        query = query.filter(models.User.role == role)
    return query.order_by(models.User.created_at.desc()).all()


def delete_user(db: Session, user: models.User) -> None:
    db.delete(user)
    db.commit()


def reset_user_password(db: Session, user: models.User, new_password: str) -> None:
    user.password = hash_password(new_password)  # type: ignore
    db.commit()


# ------------------------------------------------------------- Tickets -----
def _decorate_ticket(ticket: models.Ticket) -> models.Ticket:
    """Attaches display-friendly names the response model expects."""
    ticket.customer_name = ticket.customer.name if ticket.customer else None
    ticket.agent_name = ticket.agent.name if ticket.agent else None
    return ticket


# def create_ticket(db: Session, user_id: int, ticket_in: schemas.TicketCreate,
#                    attachment_filename: Optional[str] = None,
#                    original_filename: Optional[str] = None) -> models.Ticket:
#     ticket = models.Ticket(
#         user_id=user_id,
#         subject=ticket_in.subject,
#         description=ticket_in.description,
#         priority=ticket_in.priority,
#         attachment_filename=attachment_filename,
#         original_filename=original_filename,
#     )
#     db.add(ticket)
#     db.commit()
#     db.refresh(ticket)
#     return _decorate_ticket(ticket)

def create_ticket(db: Session, user_id: int, ticket_in: schemas.TicketCreate, **kwargs: Any) -> models.Ticket:
    ticket = models.Ticket(user_id=user_id, **ticket_in.model_dump(), **kwargs)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    
    # Use int() to satisfy the type checker
    ticket_id = int(ticket.id) # type: ignore
    create_audit_log(db, ticket_id, user_id, "CREATED", {"new": ticket_in.model_dump()})
    return _decorate_ticket(ticket)

def create_audit_log(db: Session, ticket_id: int, user_id: int, action: str, changes: Optional[Dict[str, Any]] = None):
    log = models.AuditLog(
        ticket_id=ticket_id,
        performed_by=user_id,
        action=action,
        changes=changes
    )
    db.add(log)
    db.commit()


# def get_ticket(db: Session, ticket_id: int) -> Optional[models.Ticket]:
#     ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
#     return _decorate_ticket(ticket) if ticket else None

def get_ticket(db: Session, ticket_id: int) -> Optional[models.Ticket]:
    ticket = db.query(models.Ticket).filter(
        models.Ticket.id == ticket_id, 
        models.Ticket.deleted_at == None  # Don't show deleted tickets
    ).first()
    return _decorate_ticket(ticket) if ticket else None

def list_tickets_for_user(db: Session, user_id: int):
    tickets = (
        db.query(models.Ticket)
        .filter(models.Ticket.user_id == user_id)
        .order_by(models.Ticket.created_at.desc())
        .all()
    )
    return [_decorate_ticket(t) for t in tickets]


def list_all_tickets(db: Session, status: Optional[str] = None, priority: Optional[str] = None,
                      customer_id: Optional[int] = None, search: Optional[str] = None):
    query = db.query(models.Ticket).filter(models.Ticket.deleted_at == None)
    if status:
        query = query.filter(models.Ticket.status == status)
    if priority:
        query = query.filter(models.Ticket.priority == priority)
    if customer_id:
        query = query.filter(models.Ticket.user_id == customer_id)
    if search:
        like = f"%{search}%"
        query = query.join(models.User, models.Ticket.user_id == models.User.id).filter(
            (models.Ticket.subject.ilike(like))
            | (models.Ticket.description.ilike(like))
            | (models.User.name.ilike(like))
            | (models.User.email.ilike(like))
        )
    tickets = query.order_by(models.Ticket.created_at.desc()).all()
    return [_decorate_ticket(t) for t in tickets]


# def update_ticket_fields(db: Session, ticket: models.Ticket, ticket_update: schemas.TicketUpdate) -> models.Ticket:
#     data = ticket_update.model_dump(exclude_unset=True)
#     for field, value in data.items():
#         setattr(ticket, field, value)
#     ticket.updated_at = datetime.utcnow()  # type: ignore
#     db.commit()
#     db.refresh(ticket)
#     return _decorate_ticket(ticket)

def update_ticket_fields(db: Session, ticket: models.Ticket, ticket_update: schemas.TicketUpdate, user_id: int) -> models.Ticket:
    old_data = {"subject": str(ticket.subject), "description": str(ticket.description)}
    new_data = ticket_update.model_dump(exclude_unset=True)
    
    for field, value in new_data.items():
        setattr(ticket, field, value)
    
    db.commit()
    ticket_id = int(ticket.id) # type: ignore
    create_audit_log(db, ticket_id, user_id, "UPDATED", {"old": old_data, "new": new_data})
    return _decorate_ticket(ticket)


# def admin_update_ticket(db: Session, ticket: models.Ticket, admin_update: schemas.TicketAdminUpdate) -> models.Ticket:
#     data = admin_update.model_dump(exclude_unset=True)
#     for field, value in data.items():
#         setattr(ticket, field, value)
#     ticket.updated_at = datetime.utcnow()  # type: ignore
#     db.commit()
#     db.refresh(ticket)
#     return _decorate_ticket(ticket)

def admin_update_ticket(db: Session, ticket: models.Ticket, admin_update: schemas.TicketAdminUpdate, admin_id: int) -> models.Ticket:
    old_data = {"status": str(ticket.status), "priority": str(ticket.priority)}
    new_data = admin_update.model_dump(exclude_unset=True)
    
    for field, value in new_data.items():
        setattr(ticket, field, value)
        
    db.commit()
    ticket_id = int(ticket.id) # type: ignore
    create_audit_log(db, ticket_id, admin_id, "ADMIN_UPDATE", {"old": old_data, "new": new_data})
    return _decorate_ticket(ticket)

# def delete_ticket(db: Session, ticket: models.Ticket) -> None:
#     db.delete(ticket)
#     db.commit()
def delete_ticket(db: Session, ticket: models.Ticket, user_id: int) -> None:
    # Use setattr to avoid "Cannot assign to attribute" error
    setattr(ticket, "deleted_at", datetime.utcnow())
    ticket_id = int(ticket.id) # type: ignore
    create_audit_log(db, ticket_id, user_id, "SOFT_DELETED")
    db.commit()

def get_ticket_including_deleted(db: Session, ticket_id: int) -> Optional[models.Ticket]:
    # Notice we REMOVED the 'deleted_at == None' filter here
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    return _decorate_ticket(ticket) if ticket else None

def get_ticket_history(db: Session, ticket_id: int):
    return db.query(models.AuditLog).filter(models.AuditLog.ticket_id == ticket_id).order_by(models.AuditLog.timestamp.desc()).all()

# ------------------------------------------------------------ Comments -----
def create_comment(db: Session, ticket_id: int, user_id: int, comment_in: schemas.CommentCreate) -> models.Comment:
    comment = models.Comment(
        ticket_id=ticket_id,
        user_id=user_id,
        comment=comment_in.comment,
        is_internal=comment_in.is_internal,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    comment.author_name = comment.author.name
    comment.author_role = comment.author.role
    return comment


def list_comments_for_ticket(db: Session, ticket_id: int, include_internal: bool):
    query = db.query(models.Comment).filter(models.Comment.ticket_id == ticket_id)
    if not include_internal:
        query = query.filter(models.Comment.is_internal.is_(False))
    comments = query.order_by(models.Comment.created_at.asc()).all()
    for c in comments:
        c.author_name = c.author.name
        c.author_role = c.author.role
    return comments


# -------------------------------------------------------- Notifications ----
def create_notification(db: Session, user_id: int, message: str, ticket_id: Optional[int] = None) -> models.Notification:
    note = models.Notification(user_id=user_id, ticket_id=ticket_id, message=message)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def list_notifications_for_user(db: Session, user_id: int):
    return (
        db.query(models.Notification)
        .filter(models.Notification.user_id == user_id)
        .order_by(models.Notification.created_at.desc())
        .all()
    )


def mark_notification_read(db: Session, notification: models.Notification) -> models.Notification:
    notification.is_read = True  # type: ignore
    db.commit()
    db.refresh(notification)
    return notification


# --------------------------------------------------------------- Admin -----
def get_analytics(db: Session) -> dict:
    total_tickets = db.query(models.Ticket).count()
    total_users = db.query(models.User).filter(models.User.role == models.RoleEnum.user).count()

    status_counts = dict(
        db.query(models.Ticket.status, func.count(models.Ticket.id))
        .group_by(models.Ticket.status).all()  # type: ignore
    )
    priority_counts = dict(
        db.query(models.Ticket.priority, func.count(models.Ticket.id))
        .group_by(models.Ticket.priority).all()  # type: ignore
    )

    monthly_raw = (
        db.query(
            extract("year", models.Ticket.created_at).label("year"),
            extract("month", models.Ticket.created_at).label("month"),
            func.count(models.Ticket.id).label("count"),
        )
        .group_by("year", "month")
        .order_by("year", "month")
        .all()
    )
    tickets_per_month = [
        {"label": f"{int(row.year)}-{int(row.month):02d}", "count": row.count}
        for row in monthly_raw
    ]

    active_raw = (
        db.query(models.User.name, func.count(models.Ticket.id).label("count"))
        .join(models.Ticket, models.Ticket.user_id == models.User.id)
        .group_by(models.User.id)
        .order_by(func.count(models.Ticket.id).desc())
        .limit(5)
        .all()
    )
    most_active_users = [{"name": row.name, "count": row.count} for row in active_raw]

    return {
        "total_tickets": total_tickets,
        "total_users": total_users,
        "status_counts": {k.value if hasattr(k, "value") else k: v for k, v in status_counts.items()},  # type: ignore
        "priority_counts": {k.value if hasattr(k, "value") else k: v for k, v in priority_counts.items()},  # type: ignore
        "tickets_per_month": tickets_per_month,
        "most_active_users": most_active_users,
    }


# --------------------------------------------------------------- sudit logs -----
