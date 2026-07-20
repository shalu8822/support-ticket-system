from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator

from models import RoleEnum, PriorityEnum, StatusEnum


# ---------------------------------------------------------------- Users ----
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        return v

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be blank.")
        return v.strip()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: RoleEnum
    created_at: datetime


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# ---------------------------------------------------------------- Auth -----
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: RoleEnum


class TokenData(BaseModel):
    user_id: Optional[int] = None


# -------------------------------------------------------------- Tickets ----
class TicketCreate(BaseModel):
    subject: str
    description: str
    priority: PriorityEnum = PriorityEnum.medium


class TicketUpdate(BaseModel):
    """Customer can edit these fields only while the ticket is still Open."""
    subject: Optional[str] = None
    description: Optional[str] = None


class TicketAdminUpdate(BaseModel):
    status: Optional[StatusEnum] = None
    priority: Optional[PriorityEnum] = None
    assigned_to: Optional[int] = None


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    subject: str
    description: str
    priority: PriorityEnum
    status: StatusEnum
    assigned_to: Optional[int]
    attachment_filename: Optional[str]
    original_filename: Optional[str]
    created_at: datetime
    updated_at: datetime
    customer_name: Optional[str] = None
    agent_name: Optional[str] = None


# ------------------------------------------------------------- Comments ----
class CommentCreate(BaseModel):
    comment: str
    is_internal: bool = False


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    user_id: int
    comment: str
    is_internal: bool
    created_at: datetime
    author_name: Optional[str] = None
    author_role: Optional[RoleEnum] = None


# --------------------------------------------------------- Notifications ---
class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: Optional[int]
    message: str
    is_read: bool
    created_at: datetime


# ------------------------------------------------------------ Analytics ----
class AnalyticsOut(BaseModel):
    total_tickets: int
    total_users: int
    status_counts: dict
    priority_counts: dict
    tickets_per_month: List[dict]
    most_active_users: List[dict]
