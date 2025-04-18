from django_elasticsearch_dsl import Document
from django_elasticsearch_dsl.registries import registry
from .models import Exam

@registry.register_document
class ExamDocument(Document):
    class Index:
        # Nome do índice no Elasticsearch
        name = 'exams'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        model = Exam  # Modelo que será indexado
        fields = [
            'id',
            'title',
            'description',
            'is_active',
            'created_at',
        ]