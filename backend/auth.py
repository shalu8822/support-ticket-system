"""
Auth *dependencies* shared across routers -- current-user resolution and
role checks. The actual /register and /login HTTP routes live in
routers/auth.py; this module is what the rest of the app imports to
enforce "who is calling, and are they allowed to do this".
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from security import decode_access_token
import models

__all__ = ["get_current_user", "require_admin"]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    payload = decode_access_token(token)
    if payload is None:
        raise CREDENTIALS_EXCEPTION

    user_id = payload.get("sub")
    if user_id is None:
        raise CREDENTIALS_EXCEPTION

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None:
        raise CREDENTIALS_EXCEPTION
    return user


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    user_role = getattr(current_user, 'role')  # type: models.RoleEnum
    if user_role != models.RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires admin (support agent) privileges.",
        )
    return current_user
