from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from app.db.session import get_db
from app.db.models.user import User
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user as get_current_admin
)
from app.core.config import settings

router = APIRouter()


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class AdminInfo(BaseModel):
    username: str
    email: str


class AdminCreate(BaseModel):
    username: str
    email: str
    password: str


@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=AdminInfo)
async def get_me(admin: str = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == admin))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return AdminInfo(username=user.username, email=user.email)


@router.post("/create-admin", status_code=status.HTTP_201_CREATED)
async def create_admin(admin_data: AdminCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == admin_data.username))
    if result.scalars().first():
        # Already exists, just return success so Make doesn't error out repeatedly if run multiple times
        return {"message": "Admin already exists", "username": admin_data.username}
        
    hashed_password = get_password_hash(admin_data.password)
    db_user = User(
        username=admin_data.username,
        email=admin_data.email,
        hashed_password=hashed_password,
        is_admin=True
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return {"message": "Admin created successfully", "username": db_user.username}