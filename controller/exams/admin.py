from django.contrib import admin
from .models import *  # Importa todos os modelos

# Exams
admin.site.register(Exam)
admin.site.register(Question)
admin.site.register(Choice)
admin.site.register(Participant)
admin.site.register(Answer)