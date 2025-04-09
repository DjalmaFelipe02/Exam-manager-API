from celery import shared_task
from django.db import transaction
from django.db.models import F, Subquery, OuterRef
from .models import Participant, Answer
import logging

logger = logging.getLogger(__name__)

@shared_task
def grade_answers(answer_id):
    try:
        # Busca todas as relações necessárias em uma query
        answer = Answer.objects.select_related(
            'choice', 
            'question', 
            'participant'
        ).get(id=answer_id)
        
        if answer.choice.is_correct:
            # Atualização atômica do score
            Participant.objects.filter(id=answer.participant.id).update(
                score=F('score') + answer.question.points
            )
        update_ranking.delay(answer.participant.exam_id)
        
    except Answer.DoesNotExist as e:
        logger.error(f"Resposta {answer_id} não encontrada: {str(e)}")
    except Exception as e:
        logger.error(f"Erro ao corrigir resposta {answer_id}: {str(e)}")

@shared_task
def update_ranking(exam_id):
    try:
        with transaction.atomic():
            # Subquery para obter a posição correta
            ranked = Participant.objects.filter(
                exam_id=exam_id,
                score__gte=OuterRef('score')
            ).values('exam_id').annotate(
                count=models.Count('id')
            ).values('count')
            
            # Atualização em massa
            Participant.objects.filter(exam_id=exam_id).update(
                rank=Subquery(ranked)
            )
            
    except Exception as e:
        logger.error(f"Erro ao atualizar ranking da prova {exam_id}: {str(e)}")