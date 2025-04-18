from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Configurar o módulo de configurações do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Criar a instância do Celery
app = Celery('core')

# Carregar configurações do Celery a partir do arquivo de configurações do Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descobrir automaticamente tarefas definidas nos apps instalados
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')