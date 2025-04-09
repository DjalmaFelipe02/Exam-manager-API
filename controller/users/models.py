from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ADMIN = 'ADMIN'
    PARTICIPANT = 'PARTICIPANT'
    ROLE_CHOICES = [
        (ADMIN, 'Administrador'),
        (PARTICIPANT, 'Participante'),
    ]
    role = models.CharField(max_length=12, 
                            choices=ROLE_CHOICES,
                            default=PARTICIPANT)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)

    groups = None
    user_permissions = None

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        # Se for superuser, define como ADMIN
        if self.is_superuser:
            self.role = self.ADMIN
        super().save(*args, **kwargs)
    @property
    def created_at(self):
        return self.date_joined  # Mapeia date_joined para created_at
