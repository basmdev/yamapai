import os

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
    os.path.abspath(os.path.dirname(__file__)), "database.db"
)
SECRET_CODE = os.getenv("SECRET_CODE")
