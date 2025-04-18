# tests.py
from django.test import TestCase
from ninja.testing import TestClient
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from unittest.mock import patch

from users.models import User
from .models import Exam, Question, Choice, Participant, Answer
from .api import router
from .schemas import ExamIn, QuestionIn, ChoiceIn, ParticipantIn, AnswerIn


client = TestClient(router)

class BaseExamTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin_user', password='adminpass', role='ADMIN')
        self.participant = User.objects.create_user(username='participant_user', password='participantpass', role='PARTICIPANT')
        self.admin_token = self._create_test_token(self.admin)
        self.participant_token = self._create_test_token(self.participant)

        self.exam = Exam.objects.create(
            title='Prova de Matemática',
            description='Prova sobre álgebra linear',
            is_active=True,
            duration=60,
            max_attempts=2,
            created_by=self.admin,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(days=7)
        )
        self.question = Question.objects.create(
            exam=self.exam,
            text='Quanto é 2 + 2?',
            points=10,
            question_type='MCQ'
        )
        self.correct_choice = Choice.objects.create(
            question=self.question,
            text='4',
            is_correct=True
        )
        self.wrong_choice = Choice.objects.create(
            question=self.question,
            text='5',
            is_correct=False
        )
        self.participant_obj = None

    def _create_test_token(self, user):
        from datetime import datetime, timedelta
        import jwt, os
        SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key-123")
        return jwt.encode({"sub": str(user.id), "exp": datetime.utcnow() + timedelta(minutes=60)}, SECRET_KEY, algorithm="HS256")
    
    def _get_token(self, username, password):
        user = User.objects.get(username=username)
        return self._create_test_token(user)

    def _auth_header(self, token):
        return {'Authorization': f'Bearer {token}'}
    
    

class TaskTests(BaseExamTest):
    @patch('exams.tasks.update_ranking.delay')
    def test_grade_correct_answer_increases_score(self, mock_ranking):
        answer = Answer.objects.create(
            participant=self.participant_obj,
            question=self.question,
            choice=self.correct_choice,
            is_correct=True
        )
        from exams.tasks import grade_answers
        grade_answers(answer.id)
        self.participant_obj.refresh_from_db()
        self.assertEqual(self.participant_obj.score, self.question.points)
        mock_ranking.assert_called_once_with(self.exam.id)

    def test_grade_answers_with_invalid_id_logs_error(self):
        from exams.tasks import grade_answers
        with self.assertLogs('exams.tasks', level='ERROR') as cm:
            grade_answers(-999)
        self.assertIn('não encontrada', cm.output[0])

    def test_update_ranking_orders_correctly(self):
        from exams.tasks import update_ranking
        user2 = User.objects.create_user('u2')
        Participant.objects.create(user=user2, exam=self.exam, score=15)
        update_ranking(self.exam.id)
        ranks = list(Participant.objects.filter(exam=self.exam).order_by('rank').values_list('score', flat=True))
        ranks = sorted(ranks, reverse=True)  # Ordena em ordem decrescente
        self.assertEqual(ranks, [15.0, 0.0])  # Verificando se o ranking está correto

class AuthPermissionTests(BaseExamTest):
    def test_admin_can_delete_exam(self):
        resp = client.delete(f"/exams/{self.exam.id}", headers=self._auth_header(self.admin_token))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Exam.objects.filter(id=self.exam.id).exists())

    def test_register_participant(self):
        # Cria um novo usuário para o teste
        new_user = User.objects.create_user(
            username='new_test_user',
            password='testpass',
            role='PARTICIPANT'
        )
        new_token = self._create_test_token(new_user)
        
        payload = {'exam_id': self.exam.id}
        resp = client.post("/participants", 
                        json=payload, 
                        headers=self._auth_header(new_token))
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['current_attempt'], 1)


    def test_participant_cannot_create_exam(self):
        payload = ExamIn(
            title='Não autorizado',
            description='Tentativa de criação',
            duration=30,
            max_attempts=1
        ).dict()
        resp = client.post("/exams", json=payload, headers=self._auth_header(self.participant_token))
        self.assertEqual(resp.status_code, 403)

    def test_list_exams_search_filter(self):
        Exam.objects.create(title='Álgebra Linear', description='Matemática', duration=30, max_attempts=1, created_by=self.admin)
        resp = client.get("/exams?search=Álgebra")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()['items']), 1)

    def test_participant_can_list_active_exams(self):
        Exam.objects.create(title='Inativo', is_active=False, duration=60, max_attempts=1, created_by=self.admin)
        resp = client.get("/exams/active")
        print(resp.json())  # Adicione este log para depuração
        self.assertIsInstance(data, list)  # Verifica se a resposta é uma lista
        titles = [e['title'] for e in resp.json()]
        self.assertIn('Prova de Matemática', titles)
        self.assertNotIn('Inativo', titles)

    def test_get_exam_by_id(self):
        resp = client.get(f"/exams/{self.exam.id}", headers=self._auth_header(self.admin_token))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['title'], self.exam.title)

    def test_search_exams(self):
        Exam.objects.create(title='Álgebra Linear', description='Prova sobre álgebra', is_active=True, created_by=self.admin)
        Exam.objects.create(title='Geometria', description='Prova sobre formas', is_active=True, created_by=self.admin)

        resp = client.get("/exams/search?query=Álgebra")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()), 1)
        self.assertIn('Álgebra Linear', [exam['title'] for exam in resp.json()])

    def test_max_attempts_limit(self):
        exam = Exam.objects.create(
            title='Test Max Attempts',
            description='Test exam',
            max_attempts=2,
            duration=60,
            created_by=self.admin
        )
        
        # Primeira tentativa
        resp1 = client.post("/participants", 
                        json={'exam_id': exam.id}, 
                        headers=self._auth_header(self.participant_token))
        self.assertEqual(resp1.status_code, 201)
        
        # Segunda tentativa
        resp2 = client.post("/participants", 
                        json={'exam_id': exam.id}, 
                        headers=self._auth_header(self.participant_token))
        self.assertEqual(resp2.status_code, 201)
        
        # Terceira tentativa (deve falhar)
        resp3 = client.post("/participants", 
                        json={'exam_id': exam.id}, 
                        headers=self._auth_header(self.participant_token))
        self.assertEqual(resp3.status_code, 400)
        self.assertIn("máximo de tentativas", resp3.json()['detail'])

    def test_submit_answer_with_invalid_token(self):
        payload = {
            'question_id': self.question.id,
            'choice_id': self.correct_choice.id
        }
        resp = client.post("/answers", json=payload, headers={'Authorization': 'Bearer invalid.token'})
        self.assertEqual(resp.status_code, 401)

    def test_submit_answer_with_expired_token(self):
        import jwt, os
        from datetime import datetime, timedelta
        expired_token = jwt.encode({"sub": str(self.participant.id), "exp": datetime.utcnow() - timedelta(hours=1)}, os.getenv("SECRET_KEY", "fallback-secret-key-123"), algorithm="HS256")
        payload = {
            'question_id': self.question.id,
            'choice_id': self.correct_choice.id
        }
        resp = client.post("/answers", json=payload, headers={'Authorization': f'Bearer {expired_token}'})
        self.assertEqual(resp.status_code, 401)

    def test_admin_can_update_question(self):
        update_data = {
            'exam_id': self.exam.id,
            'text': 'Quanto é 10 + 10?',
            'points': 20,
            'question_type': 'MCQ'
        }
        resp = client.put(f"/questions/{self.question.id}", json=update_data, headers=self._auth_header(self.admin_token))
        self.assertEqual(resp.status_code, 200)
        self.question.refresh_from_db()
        self.assertEqual(self.question.text, 'Quanto é 10 + 10?')
        self.assertEqual(self.question.points, 20)

    def test_participant_cannot_update_question(self):
        update_data = {
            'exam_id': self.exam.id,
            'text': 'Alteração não permitida',
            'points': 50,
            'question_type': 'MCQ'
        }
        resp = client.put(f"/questions/{self.question.id}", json=update_data, headers=self._auth_header(self.participant_token))
        self.assertEqual(resp.status_code, 403)
    def test_participant_register_twice(self):
        payload = {'exam_id': self.exam.id}
        resp1 = client.post("/participants", json=payload, headers=self._auth_header(self.participant_token))
        self.assertEqual(resp1.status_code, 400)
        self.assertIn('já está inscrito', resp1.json()['detail'])

    def test_submit_duplicate_answer(self):
        payload = {'question_id': self.question.id, 'choice_id': self.correct_choice.id}
        first = client.post("/answers", json=payload, headers=self._auth_header(self.participant_token))
        self.assertEqual(first.status_code, 200)
        second = client.post("/answers", json=payload, headers=self._auth_header(self.participant_token))
        self.assertEqual(second.status_code, 400)
        self.assertIn('já respondida', second.json()['detail'])
    
    def test_admin_can_create_and_update_choice(self):
        new_payload = {"question_id": self.question.id, "text": "New Choice", "is_correct": True}
        create = client.post("/choices", json=new_payload, headers=self._auth_header(self.admin_token))
        self.assertEqual(create.status_code, 201)  # Esperando sucesso na criação
        
        # Teste de atualização
        update_data = {
        "question_id": self.question.id,
        "text": "Updated Choice",
        "is_correct": True
        }
        update = client.put(f"/choices/{create.json()['id']}", json=update_data, headers=self._auth_header(self.admin_token))
        self.assertEqual(update.status_code, 200)  # Esperando sucesso na atualização

    def test_participant_cannot_update_choice(self):
        payload = {
            'question_id': self.question.id,
            'text': 'Hacker update',
            'is_correct': True
        }
        resp = client.put(f"/choices/{self.correct_choice.id}", json=payload, headers=self._auth_header(self.participant_token))
        self.assertEqual(resp.status_code, 403)

    def test_submit_wrong_answer_and_check_ranking(self):
        payload = {'question_id': self.question.id, 'choice_id': self.wrong_choice.id}
        resp = client.post("/answers", json=payload, headers=self._auth_header(self.participant_token))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()['is_correct'])
        self.participant_obj.refresh_from_db()
        self.assertEqual(self.participant_obj.score, 0)
        # Criar participante com nota maior
        user2 = User.objects.create_user("runner_up")
        Participant.objects.create(user=user2, exam=self.exam, score=20)
        ranking = client.get(f"/exams/{self.exam.id}/ranking")
        self.assertEqual(ranking.status_code, 200)
        scores = [r['score'] for r in ranking.json()]
        self.assertEqual(scores, [20, 0])

