from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Модель пользователя."""

    id = Column(Integer, primary_key=True)
    username = Column(String(150), unique=True, nullable=False)
    password = Column(String(150), nullable=False)

    def set_password(self, password):
        self.password = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password):
        return check_password_hash(self.password, password)


class Client(db.Model):
    """Модель клиента."""

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False)
    csv_file_path = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=None)
    check_frequency = Column(Integer, nullable=True)
    auto_check = Column(Boolean, default=False)


class Keyword(db.Model):
    """Модель ключевых слов."""

    id = Column(Integer, primary_key=True)
    word = Column(String(64), nullable=False)


class Affiliate(db.Model):
    """Модель филиала."""

    id = Column(Integer, primary_key=True)
    address = Column(String(64), nullable=False)
    longitude = Column(String(64), nullable=False)
    latitude = Column(String(64), nullable=False)
    result = Column(String(64), nullable=False, default="Неизвестно")
    check_time = Column(String(64), nullable=False, default="Неизвестно")
