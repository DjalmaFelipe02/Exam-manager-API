from django.urls import path
from ninja import NinjaAPI
from .api import router as auth_router

api = NinjaAPI(
    title="Users API",
    version="1.0",
    urls_namespace="users_api",
)

# Registrar o roteador de autenticação
api.add_router("/auth/", auth_router)

urlpatterns = [
    path("", api.urls),  # Encapsular as URLs do NinjaAPI
]