import jwt
from datetime import datetime, timedelta
from django.test import TestCase
from ninja import NinjaAPI
from ninja.testing import TestClient
from django.contrib.auth import get_user_model
from exams.api import router
from exams.models import Exam, Question, Choice, Participant, Answer

User = get_user_model()

SECRET_KEY = "fallback-secret-key-123"
ALGORITHM = "HS256"


def generate_token(user):
    return jwt.encode({
        "sub": str(user.id),
        "exp": datetime.utcnow() + timedelta(hours=3)
    }, SECRET_KEY, algorithm=ALGORITHM)


class BaseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.api = NinjaAPI(version="test", urls_namespace="test_api")
        cls.api.add_router("", router)
        cls.client = TestClient(cls.api)

        cls.admin = User.objects.create_user(username="admin", password="123", role="ADMIN", is_staff=True)
        cls.participant = User.objects.create_user(username="user", password="123", role="PARTICIPANT")

        cls.admin_token = generate_token(cls.admin)
        cls.participant_token = generate_token(cls.participant)


class ExamTests(BaseTest):
    def test_list_active_exams_public(self):
        Exam.objects.create(
            title="Prova pública",
            description="Descrição",
            is_active=True,
            duration=60,
            max_attempts=1,
            created_by=self.admin
        )
        response = self.client.get("/exams/active")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 1)

    def test_admin_can_create_exam(self):
        payload = {
            "title": "Nova Prova",
            "description": "Teste",
            "is_active": True,
            "duration": 60,
            "max_attempts": 2
        }
        response = self.client.post("/exams", json=payload,
                                    headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(response.status_code, 201)

    def test_participant_cannot_create_exam(self):
        payload = {
            "title": "Teste não autorizado",
            "description": "Negado",
            "is_active": True,
            "duration": 30,
            "max_attempts": 1
        }
        response = self.client.post("/exams", json=payload,
                                    headers={"Authorization": f"Bearer {self.participant_token}"})
        self.assertEqual(response.status_code, 403)


class ParticipantTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.exam = Exam.objects.create(
            title="Exame 1",
            description="Descrição",
            is_active=True,
            duration=60,
            max_attempts=1,
            created_by=self.admin
        )

    def test_register_success(self):
        response = self.client.post("/participants",
                                    json={"exam_id": self.exam.id},
                                    headers={"Authorization": f"Bearer {self.participant_token}"})
        self.assertEqual(response.status_code, 200)

    def test_register_duplicate(self):
        Participant.objects.create(user=self.participant, exam=self.exam)
        response = self.client.post("/participants",
                                    json={"exam_id": self.exam.id},
                                    headers={"Authorization": f"Bearer {self.participant_token}"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("inscrito", response.json()["detail"])


class AnswerTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.exam = Exam.objects.create(
            title="Exame Resposta",
            is_active=True,
            duration=60,
            max_attempts=1,
            created_by=self.admin
        )
        self.question = Question.objects.create(
            exam=self.exam,
            text="Capital do Brasil?",
            points=10,
            question_type="MCQ"
        )
        self.choice = Choice.objects.create(
            question=self.question,
            text="Brasília",
            is_correct=True
        )
        self.participant = Participant.objects.create(user=self.participant, exam=self.exam)

    def test_submit_answer_success(self):
        response = self.client.post("/answers", json={
            "question_id": self.question.id,
            "choice_id": self.choice.id
        }, headers={"Authorization": f"Bearer {self.participant_token}"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_correct"])

    def test_submit_duplicate_answer(self):
        Answer.objects.create(
            participant=self.participant,
            question=self.question,
            choice=self.choice,
            is_correct=True
        )
        response = self.client.post("/answers", json={
            "question_id": self.question.id,
            "choice_id": self.choice.id
        }, headers={"Authorization": f"Bearer {self.participant_token}"})
        self.assertEqual(response.status_code, 400)

    def test_invalid_choice_question_mismatch(self):
        other_question = Question.objects.create(
            exam=self.exam,
            text="Outro?",
            points=5,
            question_type="MCQ"
        )
        response = self.client.post("/answers", json={
            "question_id": other_question.id,
            "choice_id": self.choice.id
        }, headers={"Authorization": f"Bearer {self.participant_token}"})
        self.assertEqual(response.status_code, 400)


class RankingTests(BaseTest):
    def test_ranking_order(self):
        exam = Exam.objects.create(
            title="Ranking Test",
            is_active=True,
            duration=60,
            max_attempts=1,
            created_by=self.admin
        )
        Participant.objects.create(user=self.participant, exam=exam, score=15)
        response = self.client.get(f"/exams/{exam.id}/ranking")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data), 1)
        self.assertEqual(data[0]["user_id"], self.participant.id)
        self.assertEqual(data[0]["score"], 15)
