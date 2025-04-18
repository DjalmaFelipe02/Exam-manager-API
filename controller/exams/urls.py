from django.urls import path
from ninja import NinjaAPI
from .api import router as exams_router

api = NinjaAPI(
    title="Exams API",
    version="1.0",
    urls_namespace="exams_api",
)

# Registrar o roteador de exames
api.add_router("/exams/", exams_router)

urlpatterns = [
    path("", api.urls),  # Encapsular as URLs do NinjaAPI
]