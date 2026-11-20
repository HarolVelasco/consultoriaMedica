from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_user_by_email,
    hash_password,
)
from ..database import get_db
from ..models import Usuario
from ..schemas import Token, UsuarioCreate, UsuarioLogin, UsuarioOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/registro", response_model=UsuarioOut, status_code=201)
def registro(datos: UsuarioCreate, db: Session = Depends(get_db)):
    if get_user_by_email(db, datos.email):
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    user = Usuario(
        nombre=datos.nombre,
        email=datos.email.lower(),
        telefono=datos.telefono,
        hashed_password=hash_password(datos.password),
        rol="paciente",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(datos: UsuarioLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, datos.email.lower(), datos.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    token = create_access_token({"sub": user.email})
    return Token(access_token=token, usuario=UsuarioOut.model_validate(user))


@router.post("/login-form", response_model=Token)
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Compatible con OAuth2PasswordBearer (Swagger)."""
    user = authenticate_user(db, form_data.username.lower(), form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")
    token = create_access_token({"sub": user.email})
    return Token(access_token=token, usuario=UsuarioOut.model_validate(user))


@router.get("/me", response_model=UsuarioOut)
def me(current: Usuario = Depends(get_current_user)):
    return current
