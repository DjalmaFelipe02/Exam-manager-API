from enum import Enum
from ninja import Schema
from datetime import datetime
from typing import Optional
from pydantic import validator, field_validator, ConfigDict

class UserRole(str, Enum):
    ADMIN = 'ADMIN'
    PARTICIPANT = 'PARTICIPANT'

class UserCreate(Schema):
    username: str
    password: str
    role: UserRole

    class Config:
        use_enum_values = True
    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Senha deve ter pelo menos 8 caracteres")
        return v
    @field_validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username deve ter pelo menos 3 caracteres')
        if not v.isalnum():
            raise ValueError('Username deve conter apenas letras e números')
        return v
    
class UserOut(Schema):
    id: int
    username: str
    role: str
    is_active: bool = True
    created_at: datetime = None  # Campo renomeado/mapeado
    last_login: Optional[datetime] = None

    # Adicione esta configuração para mapear 'date_joined' do modelo para 'created_at' no schema
    model_config = ConfigDict(
        populate_by_name=True,  # Novo nome para allow_population_by_field_name
        alias_generator=lambda x: "date_joined" if x == "created_at" else x
    )


class UserUpdate(Schema):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

    @validator('password')
    def validate_password(cls, v):
        if v and len(v) < 8:
            raise ValueError('Senha deve ter pelo menos 8 caracteres')
        return v
    @validator('role')
    def validate_role(cls, v):
        if v and v not in [role.value for role in UserRole]:
            raise ValueError('Role inválida')
        return v

class LoginCredentials(Schema):
    username: str
    password: str

class TokenOut(Schema):
    token: str
    token_type: str = "bearer"

class ErrorResponse(Schema):
    detail: str
