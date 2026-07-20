import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

import crud
import schemas
import models
from database import get_db
from auth import require_admin  # type: ignore

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
    """Search/filter tickets by customer, subject, status, or priority."""
    return crud.list_all_tickets(
        db, status=status_filter, priority=priority, customer_id=customer_id, search=search
    )


@router.put("/tickets/{ticket_id}", response_model=schemas.TicketOut)
def update_ticket(
    ticket_id: int,
    ticket_update: schemas.TicketAdminUpdate,
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")

    old_status = ticket.status
    updated = crud.admin_update_ticket(db, ticket, ticket_update)

    if ticket_update.status is not None and ticket_update.status != old_status:
        user_id = getattr(updated, 'user_id')  # type: int
        ticket_id_val = getattr(updated, 'id')  # type: int
        status_msg = f"Your ticket #{ticket_id_val} ('{updated.subject}') status changed to {updated.status.value}."
        crud.create_notification(
            db, user_id,
            status_msg,
            ticket_id=ticket_id_val,
        )

    return updated


@router.delete("/tickets/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(
    ticket_id: int,
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    crud.delete_ticket(db, ticket)


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
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    user = crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user_role = getattr(user, 'role')  # type: models.RoleEnum
    if user_role == models.RoleEnum.admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    crud.delete_user(db, user)


@router.put("/users/{uid}/reset-password")
def reset_password(
    uid: int,
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Generates and sets a temporary password for the user (returned once)."""
    user = crud.get_user(db, uid)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user_role = getattr(user, 'role')  # type: models.RoleEnum
    if user_role == models.RoleEnum.admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    temp_password = secrets.token_urlsafe(9)
    crud.reset_user_password(db, user, temp_password)
    user_id = getattr(user, 'id')  # type: int
    return {"user_id": user_id, "temporary_password": temp_password}


# ------------------------------------------------------------ Analytics ----
@router.get("/analytics", response_model=schemas.AnalyticsOut)
def analytics(
    _admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return crud.get_analytics(db)
