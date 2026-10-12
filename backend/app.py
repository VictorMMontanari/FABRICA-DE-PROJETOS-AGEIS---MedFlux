import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from auth import auth_bp
from models import db

load_dotenv()


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.json.ensure_ascii = False
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL', 'sqlite:///medflux.db'),
        JWT_SECRET=os.getenv('JWT_SECRET'),
        JWT_EXPIRES_IN=int(os.getenv('JWT_EXPIRES_IN', 60 * 60 * 24 * 7)),
    )
    app.config.update(overrides or {})

    if not app.config['JWT_SECRET']:
        raise RuntimeError('JWT_SECRET não definido. Copie .env.example para .env e preencha.')

    origins = [o.strip() for o in os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',') if o.strip()]
    CORS(
        app,
        resources={r'/api/*': {'origins': origins}},
        methods=['GET', 'POST', 'OPTIONS'],
        allow_headers=['Content-Type', 'Authorization'],
    )

    db.init_app(app)
    app.register_blueprint(auth_bp)

    with app.app_context():
        db.create_all()

    @app.errorhandler(HTTPException)
    def handle_http_error(exc: HTTPException):
        messages = {404: 'Recurso não encontrado.', 405: 'Método não permitido.'}
        return jsonify({'message': messages.get(exc.code, exc.description)}), exc.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc: Exception):
        app.logger.exception(exc)
        return jsonify({'message': 'Erro interno no servidor.'}), 500

    return app


if __name__ == '__main__':
    create_app().run(port=int(os.getenv('PORT', 5000)), debug=os.getenv('FLASK_DEBUG') == '1')
