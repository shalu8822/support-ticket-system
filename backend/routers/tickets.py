from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

import crud
import schemas
import models
from database import get_db
from auth import get_current_user
from utils import is_allowed_file, save_upload

router = APIRouter(prefix="/tickets", tags=["Tickets"])


def _ensure_owner_or_admin(ticket: models.Ticket, current_user: models.User):
    if ticket.user_id != current_user.id and current_user.role != models.RoleEnum.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                             detail="You don't have access to this ticket.")


@router.post("", response_model=schemas.TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(
    subject: str = Form(...),
    description: str = Form(...),
    priority: models.PriorityEnum = Form(models.PriorityEnum.medium),
    attachment: Optional[UploadFile] = File(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stored_filename, original_filename = None, None
    if attachment is not None and attachment.filename:
        if not is_allowed_file(attachment.filename):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File type not allowed.")
        try:
            stored_filename, original_filename = save_upload(attachment)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    ticket_in = schemas.TicketCreate(subject=subject, description=description, priority=priority)
    return crud.create_ticket(db, current_user.id, ticket_in, stored_filename, original_filename)


@router.get("", response_model=List[schemas.TicketOut])
def list_my_tickets(
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Returns only the logged-in customer's own tickets."""
    return crud.list_tickets_for_user(db, current_user.id)


@router.get("/{ticket_id}", response_model=schemas.TicketOut)
def get_ticket(
    ticket_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    _ensure_owner_or_admin(ticket, current_user)
    return ticket


@router.put("/{ticket_id}", response_model=schemas.TicketOut)
def update_ticket(
    ticket_id: int,
    ticket_update: schemas.TicketUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    if ticket.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only edit your own tickets.")
    if ticket.status != models.StatusEnum.open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This ticket can no longer be edited because it's no longer Open.",
        )
    return crud.update_ticket_fields(db, ticket, ticket_update)


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(
    ticket_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    if ticket.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own tickets.")
    crud.delete_ticket(db, ticket)


# ------------------------------------------------------------- Comments ----
@router.post("/{ticket_id}/comments", response_model=schemas.CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(
    ticket_id: int,
    comment_in: schemas.CommentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    _ensure_owner_or_admin(ticket, current_user)

    # Only admins (support agents) may post internal-only notes.
    if comment_in.is_internal and current_user.role != models.RoleEnum.admin:
        comment_in.is_internal = False

    return crud.create_comment(db, ticket_id, current_user.id, comment_in)


@router.get("/{ticket_id}/comments", response_model=List[schemas.CommentOut])
def get_comments(
    ticket_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    _ensure_owner_or_admin(ticket, current_user)

    include_internal = current_user.role == models.RoleEnum.admin
    return crud.list_comments_for_ticket(db, ticket_id, include_internal)
