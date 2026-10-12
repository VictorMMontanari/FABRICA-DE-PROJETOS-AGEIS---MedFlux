import re
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import Blueprint, current_app, g, jsonify, request

from models import User, db

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def error(message: str, status: int):
    return jsonify({'message': message}), status


def create_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        'sub': user.id,
        'email': user.email,
        'iat': now,
        'exp': now + timedelta(seconds=current_app.config['JWT_EXPIRES_IN']),
    }
    return jwt.encode(payload, current_app.config['JWT_SECRET'], algorithm='HS256')


def session_response(user: User, status: int = 200):
    return jsonify({'token': create_token(user), 'user': user.to_profile()}), status


def require_auth(view):
    """Valida 'Authorization: Bearer <token>' e expõe o usuário em g.current_user.

    Hoje só protege /api/auth/me: o frontend ainda não envia o header nas
    rotas de triagem e unidades de saúde. Quando enviar, basta decorar essas rotas.
    """

    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get('Authorization', '')
        if not header.startswith('Bearer '):
            return error('Token inválido ou expirado.', 401)
        try:
            payload = jwt.decode(header[7:], current_app.config['JWT_SECRET'], algorithms=['HS256'])
        except jwt.PyJWTError:
            return error('Token inválido ou expirado.', 401)
        user = db.session.get(User, payload.get('sub'))
        if user is None:
            return error('Token inválido ou expirado.', 401)
        g.current_user = user
        return view(*args, **kwargs)

    return wrapper


def read_credentials(data: dict):
    email = str(data.get('email') or '').strip().lower()
    password = str(data.get('password') or '')
    return email, password


@auth_bp.post('/login')
def login():
    email, password = read_credentials(request.get_json(silent=True) or {})
    if not email or not password or not EMAIL_RE.match(email):
        return error('Email e senha são obrigatórios.', 400)

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return error('Email ou senha inválidos.', 401)

    return session_response(user)


@auth_bp.post('/register')
def register():
    data = request.get_json(silent=True) or {}
    email, password = read_credentials(data)
    name = str(data.get('name') or '').strip()
    city = str(data.get('city') or '').strip()

    if not name or not email or not password or not EMAIL_RE.match(email):
        return error('Nome, email e senha são obrigatórios.', 400)
    if len(password) < 6:
        return error('A senha deve ter no mínimo 6 caracteres.', 400)
    if User.query.filter_by(email=email).first():
        return error('Email já cadastrado.', 409)

    user = User(name=name, email=email, city=city)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return session_response(user, 201)


@auth_bp.get('/me')
@require_auth
def me():
    return jsonify(g.current_user.to_profile())
