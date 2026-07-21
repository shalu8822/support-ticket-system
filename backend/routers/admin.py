import secrets
from typing import List, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

import crud
import schemas
import models
from database import get_db
from auth import require_admin # type: ignore

router = APIRouter(prefix="/admin", tags=["Admin"])


# --------------------------------------------------------------- Tickets ---
@router.get("/tickets", response_model=List[schemas.TicketOut])
def list_all_tickets(
    status_filter: Optional[models.StatusEnum] = Query(None, alias="status"),
    priority: Optional[models.PriorityEnum] = None,
    customer_id: Optional[int] = None,
    search: Optional[str] = None,
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return crud.list_all_tickets(
        db, status=status_filter, priority=priority, customer_id=customer_id, search=search
    )


@router.put("/tickets/{ticket_id}", response_model=schemas.TicketOut)
def update_ticket(
    ticket_id: int,
    ticket_update: schemas.TicketAdminUpdate,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")

    old_status = ticket.status
    # Upgrade 1: Passing the admin 'actor' for audit logging
    updated = crud.admin_update_ticket(db, ticket, ticket_update, actor=admin)

    if ticket_update.status is not None and ticket_update.status != old_status:
        # Pylance Fix: Cast IDs to int for string formatting
        t_id = cast(int, updated.id)
        u_id = cast(int, updated.user_id)
        
        crud.create_notification(
            db, u_id,
            f"Your ticket #{t_id} ('{updated.subject}') status changed to {updated.status.value}.",
            ticket_id=t_id,
        )

    return updated


@router.delete("/tickets/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(
    ticket_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    
    # Upgrade 1: Soft delete logic
    crud.delete_ticket(db, ticket, actor=admin)


# ----------------------------------------------------------------- Users ---
@router.get("/users", response_model=List[schemas.UserOut])
def list_users(
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return crud.list_users(db, role=models.RoleEnum.user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = crud.get_user(db, user_id)
    
    # Pylance Fix: Explicitly check None and cast Enum for comparison
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    
    if cast(models.RoleEnum, user.role) == models.RoleEnum.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete an admin.")

    crud.delete_user(db, user, actor=admin)


@router.put("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = crud.get_user(db, user_id)
    
    # Pylance Fix: Explicitly check None and cast Enum for comparison
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        
    if cast(models.RoleEnum, user.role) == models.RoleEnum.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot reset admin passwords.")

    temp_password = secrets.token_urlsafe(9)
    crud.reset_user_password(db, user, temp_password, actor=admin)
    
    return {"user_id": cast(int, user.id), "temporary_password": temp_password}


# ------------------------------------------------------------ Analytics ----
@router.get("/analytics", response_model=schemas.AnalyticsOut)
def analytics(
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return crud.get_analytics(db)


# ----------------------------------------------------------- Audit Logs ----
@router.get("/audit-logs", response_model=List[schemas.AuditLogOut])
def audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Compliance trail: who changed what, and when, across tickets and users."""
    return crud.list_audit_logs(db, entity_type=entity_type, entity_id=entity_id)