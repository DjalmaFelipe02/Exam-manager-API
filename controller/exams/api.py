# api.py
from ninja import Router, Query
from ninja.pagination import paginate
from typing import List, Optional
from django.shortcuts import get_object_or_404
from django.db import transaction
from datetime import datetime
from django.db.models import Q
import logging
from .documents import ExamDocument

logger = logging.getLogger(__name__)

from celery import shared_task                              

from .models import Exam, Question, Choice, Participant, Answer
from .schemas import (
    ExamIn,
    ExamOut,
    QuestionIn,
    QuestionOut,
    ChoiceIn,
    ChoiceOut,
    ParticipantIn,
    ParticipantOut,
    AnswerIn,
    AnswerOut,
    ExamUpdate,
    ErrorResponse
)
from users.api import AuthBearer

router = Router(tags=["Exams"])

# ------------------------------ Exams Endpoints ------------------------------
@router.post('/exams', response={
        201: ExamOut,  # Sucesso
        403: ErrorResponse,  # Permissão negada
        400: ErrorResponse  # Dados inválidos
    }, auth=AuthBearer())
def create_exam(request, payload: ExamIn):
    """Cria nova prova (Admin only)"""
    if getattr(request.auth, 'role', None) != 'ADMIN':
        return 403, {"detail": "Permissão negada"}
    
    exam = Exam.objects.create(
        **payload.dict(),
        created_by=request.auth
    )
    return 201, exam

@router.get('/exams', response=List[ExamOut])
@paginate
def list_exams(request, search: Optional[str] = None, is_active: Optional[bool] = None):
    """Lista todas as provas com filtros"""
    queryset = Exam.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)
    
    return queryset.order_by('-created_at')

@router.get('/exams', response=List[ExamOut])
@paginate
def list_exams(request, search: Optional[str] = None, is_active: Optional[bool] = None, order_by: Optional[str] = '-created_at'):
    """Lista todas as provas com filtros e ordenação"""
    queryset = Exam.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)
    
    return queryset.order_by(order_by)

@router.get('/exams/{exam_id}', response=ExamOut, auth=AuthBearer())
def get_exam(request, exam_id: int):
    """Detalhes de uma prova específica"""
    return get_object_or_404(Exam, id=exam_id)

@router.put('/exams/{exam_id}', response=ExamOut, auth=AuthBearer())
def update_exam(request, exam_id: int, payload: ExamUpdate):
    """Atualiza uma prova (Admin only)"""
    if request.auth.role != 'ADMIN':
        return 403, {"detail": "Permissão negada"}
    
    exam = get_object_or_404(Exam, id=exam_id)
    for attr, value in payload.dict().items():
        setattr(exam, attr, value)
    exam.save()
    return exam

@router.delete('/exams/{exam_id}', auth=AuthBearer())
def delete_exam(request, exam_id: int):
    """Exclui uma prova (Admin only)"""
    if request.auth.role != 'ADMIN':
        return 403, {"detail": "Permissão negada"}
    
    exam = get_object_or_404(Exam, id=exam_id)
    exam.delete()
    return 200, {"detail": "Prova excluída com sucesso"}

@router.get("/exams/{exam_id}")
def get_exam_by_id(exam_id: int):
    exam = db.get_exam_by_id(exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam



@router.get('/exams/search', response=List[ExamOut], auth=None)
def search_exams(request, query: str):
    """Busca provas no Elasticsearch"""
    search = ExamDocument.search().query("multi_match", query=query, fields=["title", "description"])
    results = search.execute()
    return [hit.to_dict() for hit in results]


# ---------------------------- Questions Endpoints ----------------------------
@router.post('/questions', response=QuestionOut, auth=AuthBearer())
def create_question(request, payload: QuestionIn):
    """Cria nova questão (Admin only)"""
    if request.auth.role != 'ADMIN':
        return 403, {"detail": "Permissão negada"}
    
    exam = get_object_or_404(Exam, id=payload.exam_id)
    question = Question.objects.create(
        exam=exam,
        text=payload.text,
        points=payload.points
    )
    return question

@router.get('/questions', response=List[QuestionOut], auth=AuthBearer())
@paginate
def list_questions(request, exam_id: Optional[int] = None):
    """Lista questões com filtro por prova"""
    queryset = Question.objects.all()
    
    if exam_id:
        queryset = queryset.filter(exam_id=exam_id)
    
    return queryset.order_by('id')

@router.put('/questions/{question_id}', response={200: QuestionOut, 403: ErrorResponse}, auth=AuthBearer())
def update_question(request, question_id: int, payload: QuestionIn):
    """Atualiza uma questão (Admin only)"""
    if request.auth.role != 'ADMIN':
        return 403, {"detail": "Permissão negada"}
    
    question = get_object_or_404(Question, id=question_id)
    question.text = payload.text
    question.points = payload.points
    question.save()
    return question

@router.delete('/questions/{question_id}', auth=AuthBearer())
def delete_question(request, question_id: int):
    """Exclui uma questão (Admin only)"""
    if request.auth.role != 'ADMIN':
        return 403, {"detail": "Permissão negada"}
    
    question = get_object_or_404(Question, id=question_id)
    question.delete()
    return 200, {"detail": "Questão excluída com sucesso"}

# ----------------------------- Choices Endpoints -----------------------------
@router.post('/choices', response={201: ChoiceOut, 422: ErrorResponse}, auth=AuthBearer())
def create_choice(request, payload: ChoiceIn):
    logger.info(f"Payload recebido: {payload}")
    """Cria uma nova alternativa"""
    question = get_object_or_404(Question, id=payload.question_id)
    choice = Choice.objects.create(
        question=question,
        text=payload.text,
        is_correct=payload.is_correct
    )
    return 201, choice

@router.get('/choices', response=List[ChoiceOut], auth=AuthBearer())
@paginate
def list_choices(request, question_id: Optional[int] = None):
    """Lista alternativas com filtro por questão"""
    queryset = Choice.objects.all()
    
    if question_id:
        queryset = queryset.filter(question_id=question_id)
    
    return queryset.order_by('id')

@router.put('/choices/{choice_id}', response={200: ChoiceOut, 403: ErrorResponse}, auth=AuthBearer())
def update_choice(request, choice_id: int, payload: ChoiceIn):
    """Atualiza uma alternativa (Admin only)"""
    if request.auth.role != 'ADMIN':
        return 403, {"detail": "Permissão negada"}
    
    choice = get_object_or_404(Choice, id=choice_id)
    choice.text = payload.text
    choice.is_correct = payload.is_correct
    choice.save()
    return choice

@router.delete('/choices/{choice_id}', auth=AuthBearer())
def delete_choice(request, choice_id: int):
    """Exclui uma alternativa (Admin only)"""
    if request.auth.role != 'ADMIN':
        return 403, {"detail": "Permissão negada"}
    
    choice = get_object_or_404(Choice, id=choice_id)
    choice.delete()
    return 200, {"detail": "Alternativa excluída com sucesso"}

# -------------------------- Participants Endpoints ---------------------------
@router.post('/participants', response={201: ParticipantOut, 400: ErrorResponse}, auth=AuthBearer())
def register_participant(request, payload: ParticipantIn):
    exam = get_object_or_404(Exam, id=payload.exam_id)
# Verifica tentativas existentes
    last_attempt = Participant.objects.filter(
        user=request.auth,
        exam=exam
    ).order_by('-current_attempt').first()
    
    current_attempt = 1 if not last_attempt else last_attempt.current_attempt + 1

    if current_attempt >= exam.max_attempts:
        return 400, {"detail": f"Número máximo de tentativas ({exam.max_attempts}) atingido"}
    
    # Verifica se já está inscrito
    if Participant.objects.filter(user=request.auth, exam=exam).exists():
        return 400, {"detail": "Usuário já está inscrito nesta prova"}
    
    participant = Participant.objects.create(
        user=request.auth,
        exam=exam,
        current_attempt=current_attempt
    )
    return 201, participant

@router.get('/participants', response=List[ParticipantOut], auth=AuthBearer())
@paginate
def list_participants(request, exam_id: Optional[int] = None):
    """Lista participantes com filtro por prova"""
    queryset = Participant.objects.all()
    
    if exam_id:
        queryset = queryset.filter(exam_id=exam_id)
    
    return queryset.order_by('-score')

@router.delete('/participants/{participant_id}', auth=AuthBearer())
def delete_participant(request, participant_id: int):
    """Remove participante de uma prova (Admin only)"""
    if request.auth.role != 'ADMIN':
        return 403, {"detail": "Permissão negada"}
    
    participant = get_object_or_404(Participant, id=participant_id)
    participant.delete()
    return 200, {"detail": "Participante removido com sucesso"}

# ---------------------------- Answers Endpoints ------------------------------
@router.post('/answers', response={200: AnswerOut, 400: ErrorResponse}, auth=AuthBearer())
def submit_answer(request, payload: AnswerIn):
    """Submete resposta de uma questão"""
    question = get_object_or_404(Question, id=payload.question_id)
    choice = get_object_or_404(Choice, id=payload.choice_id)
    
    # Verifica se a alternativa pertence à questão
    if choice.question != question:
        return 400, {"detail": "Alternativa não pertence à questão"}
    
    # Verifica se o usuário está inscrito na prova
    participant = get_object_or_404(
        Participant,
        user=request.auth,
        exam=question.exam
    )
    
    # Verifica tentativa duplicada
    if Answer.objects.filter(participant=participant, question=question).exists():
        return 400, {"detail": "Questão já respondida"}
    
    with transaction.atomic():
        answer = Answer.objects.create(
            participant=participant,
            question=question,
            choice=choice,
            is_correct=choice.is_correct
        )
        
        if choice.is_correct:
            participant.score += question.points
            participant.save()
    
    return answer

@router.get('/answers', response=List[AnswerOut], auth=AuthBearer())
@paginate
def list_answers(request, participant_id: Optional[int] = None):
    """Lista respostas com filtro por participante"""
    queryset = Answer.objects.all()
    
    if participant_id:
        queryset = queryset.filter(participant_id=participant_id)
    
    return queryset.order_by('-answered_at')

# ---------------------------- Public Endpoints -------------------------------
@router.get('/exams/active', response=List[ExamOut], auth=None)
def list_active_exams(request):
    """Lista provas ativas (público)"""
    exams = Exam.objects.filter(is_active=True).order_by('-created_at')
    return list(exams)
@router.get('/exams/{exam_id}/ranking', response=List[ParticipantOut])
def get_ranking(request, exam_id: int):
    """Ranking de participantes de uma prova"""
    return Participant.objects.filter(exam_id=exam_id).order_by('-score', 'started_at')
