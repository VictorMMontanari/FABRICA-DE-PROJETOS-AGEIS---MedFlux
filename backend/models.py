import uuid
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(120), nullable=False, default='')
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def avatar_initials(self) -> str:
        parts = self.name.split()
        if not parts:
            return ''
        return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else '')).upper()

    def to_profile(self) -> dict:
        # Mesmo formato do tipo UserProfile do frontend (src/services/api.ts)
        return {'name': self.name, 'city': self.city, 'avatarInitials': self.avatar_initials}
