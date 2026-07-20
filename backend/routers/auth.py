from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import crud
import schemas
from database import get_db
from security import verify_password, create_access_token
import models

router = APIRouter(tags=["Authentication"])


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, user_in.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail="An account with this email already exists.")
    return crud.create_user(db, user_in, role=models.RoleEnum.user)


@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    OAuth2PasswordRequestForm expects `username` + `password` fields
    (that's the OAuth2 spec's field name) -- the frontend sends the
    user's email in the `username` field.
    """
    user = crud.get_user_by_email(db, form_data.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_password = getattr(user, 'password')  # type: str
    if not verify_password(form_data.password, user_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = getattr(user, 'id')  # type: int
    user_role = getattr(user, 'role')  # type: models.RoleEnum
    token = create_access_token(data={"sub": str(user_id), "role": user_role.value})
    return schemas.Token(access_token=token, role=user_role)
