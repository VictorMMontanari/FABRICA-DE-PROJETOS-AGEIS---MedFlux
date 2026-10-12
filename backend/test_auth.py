import unittest

from app import create_app
from models import User, db


class AuthTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'SQLALCHEMY_DATABASE_URI': 'sqlite://', 'JWT_SECRET': 'test-secret-with-at-least-32-bytes!!'})
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            user = User(name='Marina Santos', email='marina.santos@medflux.com', city='Marília, SP')
            user.set_password('123456')
            db.session.add(user)
            db.session.commit()

    def login(self, email='marina.santos@medflux.com', password='123456'):
        return self.client.post('/api/auth/login', json={'email': email, 'password': password})

    def test_login_success_matches_frontend_contract(self):
        res = self.login(email='  Marina.Santos@MedFlux.com ')
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(set(body), {'token', 'user'})
        self.assertEqual(body['user'], {'name': 'Marina Santos', 'city': 'Marília, SP', 'avatarInitials': 'MS'})

    def test_login_wrong_password(self):
        res = self.login(password='errada')
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.get_json(), {'message': 'Email ou senha inválidos.'})

    def test_login_unknown_email_same_message(self):
        res = self.login(email='ninguem@medflux.com')
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.get_json(), {'message': 'Email ou senha inválidos.'})

    def test_login_missing_fields(self):
        self.assertEqual(self.client.post('/api/auth/login', json={}).status_code, 400)
        self.assertEqual(self.client.post('/api/auth/login', data='x').status_code, 400)

    def test_me_with_and_without_token(self):
        token = self.login().get_json()['token']
        res = self.client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['avatarInitials'], 'MS')
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)
        bad = self.client.get('/api/auth/me', headers={'Authorization': 'Bearer lixo'})
        self.assertEqual(bad.status_code, 401)

    def test_register(self):
        payload = {'name': 'João da Silva', 'email': 'joao@medflux.com', 'password': '123456', 'city': 'Marília, SP'}
        res = self.client.post('/api/auth/register', json=payload)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()['user']['avatarInitials'], 'JS')
        self.assertEqual(self.client.post('/api/auth/register', json=payload).status_code, 409)
        short = self.client.post('/api/auth/register', json={**payload, 'email': 'x@medflux.com', 'password': '123'})
        self.assertEqual(short.status_code, 400)

    def test_cors_preflight_and_404(self):
        res = self.client.options(
            '/api/auth/login',
            headers={'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'POST'},
        )
        self.assertEqual(res.headers.get('Access-Control-Allow-Origin'), 'http://localhost:5173')
        self.assertEqual(self.client.get('/api/nada').get_json(), {'message': 'Recurso não encontrado.'})


if __name__ == '__main__':
    unittest.main()
