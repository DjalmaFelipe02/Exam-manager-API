# tests.py

import jwt
from datetime import datetime, timedelta
from django.test import TestCase
from ninja.testing import TestClient
from django.utils import timezone
from django.contrib.auth import get_user_model

from exams.models import Exam, Question, Choice, Participant, Answer
from exams.api import router

User = get_user_model()

SECRET_KEY = "fallback-secret-key-123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 3


def generate_token(user):
    return jwt.encode({
        "sub": str(user.id),
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }, SECRET_KEY, algorithm=ALGORITHM)


class BaseAPITest(TestCase):
    def setUp(self):
        self.client = TestClient(router)

        self.admin = User.objects.create_user(
            username='admin_test',
            password='adminpass',
            role=User.ADMIN,
            is_staff=True
        )
        self.participant = User.objects.create_user(
            username='participant_test',
            password='participantpass',
            role=User.PARTICIPANT
        )

        self.admin_token = generate_token(self.admin)
        self.participant_token = generate_token(self.participant)


class ExamTests(BaseAPITest):
    def test_admin_can_create_exam(self):
        payload = {
            'title': 'Prova de Lógica',
            'description': 'Avaliação inicial',
            'is_active': True,
            'duration': 60,
            'max_attempts': 1
        }
        response = self.client.post('/exams', json=payload,
                                    headers={'Authorization': f'Bearer {self.admin_token}'})
        self.assertEqual(response.status_code, 201)

    def test_participant_cannot_create_exam(self):
        payload = {
            'title': 'Tentativa',
            'description': 'Participante tentando',
            'is_active': True,
            'duration': 60,
            'max_attempts': 1
        }
        response = self.client.post('/exams', json=payload,
                                    headers={'Authorization': f'Bearer {self.participant_token}'})
        self.assertEqual(response.status_code, 403)

    def test_list_active_exams_public(self):
        Exam.objects.create(
            title='Prova pública',
            description='Descrição',
            is_active=True,
            duration=60,
            max_attempts=1,
            created_by=self.admin
        )
        response = self.client.get('/exams/active')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 1)


class ParticipantTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.exam = Exam.objects.create(
            title='Prova Teste',
            description='Descrição',
            is_active=True,
            duration=60,
            max_attempts=1,
            created_by=self.admin
        )

    def test_register_participant_successfully(self):
        response = self.client.post('/participants',
                                    json={'exam_id': self.exam.id},
                                    headers={'Authorization': f'Bearer {self.participant_token}'})
        self.assertEqual(response.status_code, 200)

    def test_register_duplicate_participant(self):
        Participant.objects.create(user=self.participant, exam=self.exam)
        response = self.client.post('/participants',
                                    json={'exam_id': self.exam.id},
                                    headers={'Authorization': f'Bearer {self.participant_token}'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('já está inscrito', response.json()['detail'])


class AnswerTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.exam = Exam.objects.create(
            title='Prova',
            description='Descrição',
            is_active=True,
            duration=60,
            max_attempts=1,
            created_by=self.admin
        )
        self.question = Question.objects.create(
            exam=self.exam,
            text='Qual a capital do Brasil?',
            points=5,
            question_type='MCQ'
        )
        self.choice = Choice.objects.create(
            question=self.question,
            text='Brasília',
            is_correct=True
        )
        self.participant_obj = Participant.objects.create(user=self.participant, exam=self.exam)

    def test_submit_valid_answer(self):
        response = self.client.post('/answers',
                                    json={'question_id': self.question.id, 'choice_id': self.choice.id},
                                    headers={'Authorization': f'Bearer {self.participant_token}'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['is_correct'])

    def test_duplicate_answer(self):
        Answer.objects.create(
            participant=self.participant_obj,
            question=self.question,
            choice=self.choice,
            is_correct=True
        )
        response = self.client.post('/answers',
                                    json={'question_id': self.question.id, 'choice_id': self.choice.id},
                                    headers={'Authorization': f'Bearer {self.participant_token}'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('já respondida', response.json()['detail'])

    def test_invalid_choice_for_question(self):
        other_question = Question.objects.create(
            exam=self.exam,
            text='Pergunta falsa',
            points=5,
            question_type='MCQ'
        )
        response = self.client.post('/answers',
                                    json={'question_id': other_question.id, 'choice_id': self.choice.id},
                                    headers={'Authorization': f'Bearer {self.participant_token}'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('não pertence', response.json()['detail'])


class RankingTests(BaseAPITest):
    def test_get_ranking(self):
        exam = Exam.objects.create(
            title='Ranking Exam',
            description='Descrição',
            is_active=True,
            duration=60,
            max_attempts=1,
            created_by=self.admin
        )
        Participant.objects.create(user=self.participant, exam=exam, score=10)
        response = self.client.get(f'/exams/{exam.id}/ranking',
                                   headers={'Authorization': f'Bearer {self.admin_token}'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data) >= 1)
        self.assertEqual(data[0]['score'], 10)
        self.assertEqual(data[0]['user_id'], self.participant.id)
