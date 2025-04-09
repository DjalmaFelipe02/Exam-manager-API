from ninja import Router
from ninja.security import HttpBearer
from ninja.pagination import paginate
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404
from .pagination import CustomPagination
import jwt  # Importação principal
from datetime import datetime, timedelta
from typing import Optional

import os
from .models import User
from .schemas import (
    UserCreate,
    UserOut,
    UserUpdate,  # Adicione esta linha
    LoginCredentials,
    TokenOut
)

router = Router(tags=["Autenticação"])

# Configurações JWT
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key-123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 3  # 3h

class AuthBearer(HttpBearer):
    def authenticate(self, request, token: str = None):
        if not token:
            return None
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            user = User.objects.get(id=user_id) if user_id else None
            if user:
                request.auth = user  # Adiciona o usuário autenticado ao request.auth
            return user
        except (jwt.ExpiredSignatureError, jwt.DecodeError, User.DoesNotExist):
            return None

@router.post("/login", response={200: TokenOut, 401: dict})
def login(request, credentials: LoginCredentials):
    """Endpoint simplificado de login"""
    if user := authenticate(username=credentials.username, password=credentials.password):
        token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            },
            SECRET_KEY,
            algorithm=ALGORITHM
        )
        return {"token": token, "token_type": "bearer"}
    return 401, {"detail": "Credenciais inválidas"}

@router.post("/register", response={201: UserOut, 400: dict})
def register(request, user_data: UserCreate):
    """Endpoint para registro de usuários"""
    if User.objects.filter(username=user_data.username).exists():
        return 400, {"detail": "Nome de usuário já existe"}
    
    user = User.objects.create(
        username=user_data.username,
        password=make_password(user_data.password),
        role=user_data.role
    )
    
    return 201, {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.date_joined
    }

@router.get("/users", response=list[UserOut], auth=AuthBearer())
@paginate(CustomPagination)
def list_users(request, search: Optional[str] = None, role: Optional[str] = None,
    is_active: Optional[bool] = None):
    """Lista todos os usuários (apenas admin)"""
    if request.auth.role != "ADMIN":
        return 403, {"detail": "Permissão negada"}
    
    queryset = User.objects.all()
    
    if search:
        queryset = queryset.filter(username__icontains=search)
    if role:
        queryset = queryset.filter(role=role)
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)
    
    return queryset.order_by('username')

@router.get("/users/{user_id}", response=UserOut, auth=AuthBearer())
def get_user(request, user_id: int):
    """Obtém detalhes de um usuário"""
    user = get_object_or_404(User, id=user_id)
    # Verifica se o usuário logado tem permissão
    if request.auth.id != user_id and request.auth.role != "ADMIN":
        return 403, {"detail": "Permissão negada"}
    return user

@router.patch("/users/{user_id}", response=UserOut, auth=AuthBearer())
def update_user(request, user_id: int, update_data: UserUpdate):
    """Atualiza usuário (próprio usuário ou admin)"""
    user = get_object_or_404(User, id=user_id)
    if request.auth.id != user_id and request.auth.role != "ADMIN":
        return 403, {"detail": "Permissão negada"}
    
    update_dict = update_data.dict(exclude_unset=True)
    
    if 'password' in update_dict:
        update_dict['password'] = make_password(update_dict['password'])
    
    for attr, value in update_dict.items():
        setattr(user, attr, value)
    
    user.save()
    return user

@router.delete(
    "/users/{user_id}",
    response={
        200: dict,  # Confirmação de sucesso
        403: dict,  # Permissão negada
        404: dict,  # Usuário não encontrado
    },
    auth=AuthBearer()
)
def delete_user(request, user_id: int):
    """Exclui um usuário (apenas admin)"""
    try:
        # Verifica permissões primeiro
        if request.auth.role != "ADMIN":
            return 403, {"detail": "Permissão negada"}
        
        user = get_object_or_404(User, id=user_id)
        user.delete()
        return 200, {"detail": "Usuário excluído com sucesso"}
        
    except User.DoesNotExist:
        return 404, {"detail": "Usuário não encontrado"}