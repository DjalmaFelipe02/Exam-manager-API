# tests.py
import jwt
from datetime import datetime, timedelta
from django.test import TestCase
from ninja.testing import TestClient
from django.contrib.auth.hashers import check_password

from .models import User
from .api import router, AuthBearer, SECRET_KEY, ALGORITHM
from .schemas import UserCreate, UserUpdate

class UserAPITests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        
        # Cria usuários de teste
        self.admin = User.objects.create_user(
            username="admintest",
            password="adminpass",
            role="ADMIN",
            is_active=True
        )
        self.participant = User.objects.create_user(
            username="participanttest",
            password="participantpass",
            role="PARTICIPANT",
            is_active=True
        )
        
        # Gera tokens
        self.admin_token = self._generate_token(self.admin)
        self.participant_token = self._generate_token(self.participant)
    
    def _generate_token(self, user):
        return jwt.encode({
            "sub": str(user.id),
            "exp": datetime.utcnow() + timedelta(minutes=180)
        }, SECRET_KEY, algorithm=ALGORITHM)
    
    # --- TESTES DE LOGIN ---
    def test_login_success(self):
        response = self.client.post("/login", json={
            "username": "admintest",
            "password": "adminpass"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.json())
    
    def test_login_invalid_credentials(self):
        response = self.client.post("/login", json={
            "username": "admintest",
            "password": "wrongpass"
        })
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Credenciais inválidas")
    
    # --- TESTES DE REGISTRO ---
    def test_register_success(self):
        response = self.client.post("/register", json={
            "username": "newuser",
            "password": "securepass123",
            "role": "PARTICIPANT"
        })
        self.assertIn(response.status_code, [201, 422])
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_duplicate_username(self):
        response = self.client.post("/register", json={
            "username": "admintest",
            "password": "pass1234",
            "role": "PARTICIPANT"
        })
        self.assertIn(response.status_code, [400, 422])
        # Verifica se a mensagem de erro está correta
        self.assertIn("Nome de usuário já existe", response.json()["detail"])
    
    # --- TESTES DE LISTAGEM ---
    def test_list_users_as_admin(self):
        response = self.client.get("/users", headers={
            "Authorization": f"Bearer {self.admin_token}"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(isinstance(data, dict))  # Verifica se a resposta é paginada
        self.assertIn("items", data)  # Verifica se há uma chave "items"
        self.assertGreaterEqual(len(data["items"]), 2)  # Deve listar admin + participant
    
    def test_list_users_as_participant(self):
        response = self.client.get("/users", headers={
            "Authorization": f"Bearer {self.participant_token}"
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"detail": "Permissão negada"})

    
    # --- TESTES DE DETALHES ---
    def test_get_own_user(self):
        response = self.client.get(f"/users/{self.participant.id}", headers={
            "Authorization": f"Bearer {self.participant_token}"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "participanttest")
    
    def test_get_other_user_as_admin(self):
        response = self.client.get(f"/users/{self.participant.id}", headers={
            "Authorization": f"Bearer {self.admin_token}"
        })
        self.assertEqual(response.status_code, 200)
    
    def test_get_other_user_as_participant(self):
        # Participante tentando acessar dados do admin
        response = self.client.get(f"/users/{self.admin.id}", headers={
            "Authorization": f"Bearer {self.participant_token}"
        })
        self.assertEqual(response.status_code, 403)
    
    # --- TESTES DE ATUALIZAÇÃO ---
    def test_update_own_user(self):
        response = self.client.patch(
            f"/users/{self.participant.id}",
            json={"username": "new_username"},
            headers={"Authorization": f"Bearer {self.participant_token}"}
        )
        self.assertEqual(response.status_code, 200)
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.username, "new_username")
    
    def test_update_password(self):
        new_password = "newsecurepass123"
        response = self.client.patch(
            f"/users/{self.participant.id}",
            json={"password": new_password},
            headers={"Authorization": f"Bearer {self.participant_token}"}
        )
        self.assertEqual(response.status_code, 200)
        self.participant.refresh_from_db()
        self.assertTrue(check_password(new_password, self.participant.password))
    
    def test_update_other_user_as_admin(self):
        response = self.client.patch(
            f"/users/{self.participant.id}",
            json={"role": "ADMIN"},  # Admin pode promover outros
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(response.status_code, 200)
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.role, "ADMIN")
    
    def test_update_other_user_as_participant(self):
        response = self.client.patch(
            f"/users/{self.admin.id}",
            json={"username": "hacked"},
            headers={"Authorization": f"Bearer {self.participant_token}"}
        )
        self.assertEqual(response.status_code, 403)
    
    # --- TESTES DE EXCLUSÃO ---
    def test_delete_user_as_admin(self):
        user_to_delete = User.objects.create_user(
            username="to_delete",
            password="pass123",
            role="PARTICIPANT"
        )
        response = self.client.delete(
            f"/users/{user_to_delete.id}",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(id=user_to_delete.id).exists())
    
    def test_delete_user_as_participant(self):
        response = self.client.delete(
            f"/users/{self.admin.id}",
            headers={"Authorization": f"Bearer {self.participant_token}"}
        )
        self.assertEqual(response.status_code, 403)
    
    def test_delete_nonexistent_user(self):
        response = self.client.delete(
            "/users/9999",  # ID inexistente
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(response.status_code, 404)
    
    # --- TESTES DE FILTROS ---
    def test_list_users_with_filters(self):
        response = self.client.get(
            "/users?role=ADMIN",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(isinstance(data, dict))  # Agora é um dict paginado
        items = data.get("items", [])
        self.assertTrue(all(user["role"] == "ADMIN" for user in items))
    
    # --- TESTES DE AUTENTICAÇÃO ---
    def test_access_with_invalid_token(self):
        response = self.client.get("/users", headers={
            "Authorization": "Bearer invalid_token"
        })
        self.assertEqual(response.status_code, 401)
    
    def test_access_without_token(self):
        response = self.client.get("/users")
        self.assertEqual(response.status_code, 401)