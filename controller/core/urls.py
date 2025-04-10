from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from users.api import router as auth_router
from exams.api import router as exams_router

api = NinjaAPI(
    title="Exam Manager API",
    version="1.0",
    docs=True,  # Documentação em /api/docs
    urls_namespace="main_api",  # Adicione um namespace único
    description="API para gerenciamento de provas",
    servers=[
        {"url": "http://localhost:8000", "description": "Local server"},
    ],
)


api.add_router("/auth/", auth_router)
api.add_router("/exams/", exams_router)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
