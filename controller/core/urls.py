from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),  # Rotas do app users
    path('api/exams/', include('exams.urls')),  # Rotas do app exams
]