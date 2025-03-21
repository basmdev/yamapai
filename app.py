import csv
import os
import threading
import time
import urllib
from datetime import datetime
from itertools import product

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

import config
from forms import LoginForm
from models import Affiliate, Client, Keyword, User, db
from webdriver.driver import get_screenshots

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER
app.config["SQLALCHEMY_DATABASE_URI"] = config.SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = config.SQLALCHEMY_TRACK_MODIFICATIONS

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


ZOOMS = [12, 13, 14, 16]  # Масштабы карт для ссылок
is_check_active = False  # Параметр автоматической проверки


def create_initial_user():
    """Создание первоначального пользователя."""
    username = os.getenv("USER")
    password = os.getenv("PASS")

    if not username or not password:
        raise ValueError("Переменные окружения USER и PASS не заданы")

    if not User.query.first():
        admin = User(username=username)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()


@login_manager.unauthorized_handler
def unauthorized():
    """Обработка запросов без авторизации."""
    flash("Войдите в систему для доступа к этой странице", "warning")
    return redirect(url_for("login"))


@login_manager.user_loader
def load_user(user_id):
    """Загрузка пользователя."""
    return db.session.get(User, int(user_id))


def process_csv_file(file_path):
    """Функция для обработки CSV файла."""
    with open(file_path, mode="r", newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            affiliate = Affiliate(
                address=row["address"],
                longitude=row["lon"],
                latitude=row["lat"],
            )
            db.session.add(affiliate)
    db.session.commit()


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """Страница профиля организации."""
    client = Client.query.first()

    if request.method == "POST":
        name = request.form.get("name")
        file = request.files.get("file")
        period = request.form.get("period", type=int)
        auto_check = True if request.form.get("auto_check") else False
        keywords_text = request.form.get("keywords", "").strip()

        if not name:
            flash("Наименование обязательно для заполнения", "danger")
            return render_template("profile.html", client=client)

        if not period:
            flash("Частота проверки обязательна для заполнения", "danger")
            return render_template("profile.html", client=client)

        client_folder = app.config["UPLOAD_FOLDER"]
        data_file_path = os.path.join(client_folder, "data.csv")

        if file:
            file_extension = os.path.splitext(file.filename)[1].lower()
            if file_extension != ".csv":
                flash("Неверный формат файла", "danger")
                return render_template("profile.html", client=client)

            os.makedirs(client_folder, exist_ok=True)
            temp_file_path = os.path.join(client_folder, "temp.csv")

            try:
                file.save(temp_file_path)

                db.session.query(Affiliate).delete()
                db.session.commit()

                process_csv_file(temp_file_path)

                if os.path.exists(data_file_path):
                    os.remove(data_file_path)

                os.rename(temp_file_path, data_file_path)

                if client:
                    client.name = name
                    client.csv_file_path = data_file_path
                    client.created_at = datetime.now()
                    client.check_frequency = period
                    client.auto_check = auto_check
                else:
                    client = Client(
                        name=name,
                        csv_file_path=data_file_path,
                        created_at=datetime.now(),
                        check_frequency=period,
                        auto_check=auto_check,
                    )
                    db.session.add(client)

                db.session.commit()

                db.session.query(Keyword).delete()
                if keywords_text:
                    keywords_list = [
                        word.strip()
                        for word in keywords_text.split(",")
                        if word.strip()
                    ]
                    for word in keywords_list:
                        db.session.add(Keyword(word=word))

                db.session.commit()

                flash("Данные изменены успешно", "success")
            except KeyError:
                if os.path.exists(data_file_path):
                    process_csv_file(data_file_path)

                os.remove(temp_file_path)
                flash("Ошибка в структуре файла CSV", "danger")
            except IntegrityError as e:
                db.session.rollback()
                flash("Ошибка в структуре файла CSV", "danger")
            except Exception as e:
                db.session.rollback()
                flash(f"Неизвестная ошибка", "danger")

            return redirect(url_for("index"))

        if client:
            client.name = name
            client.check_frequency = period
            client.auto_check = auto_check
        else:
            client = Client(name=name, check_frequency=period, auto_check=auto_check)
            db.session.add(client)

        db.session.commit()

        db.session.query(Keyword).delete()
        if keywords_text:
            keywords_list = [
                word.strip() for word in keywords_text.split(",") if word.strip()
            ]
            for word in keywords_list:
                db.session.add(Keyword(word=word))

        db.session.commit()

        flash("Данные изменены успешно", "success")
        return redirect(url_for("index"))

    file_exists = bool(client and client.csv_file_path)
    keywords = ", ".join([keyword.word for keyword in Keyword.query.all()])

    return render_template(
        "profile.html", client=client, file_exists=file_exists, keywords=keywords
    )


@app.route("/")
@login_required
def index():
    """Главная страница."""
    client = Client.query.first()
    affiliates = Affiliate.query.all()
    keywords = Keyword.query.all()
    return render_template(
        "index.html", client=client, affiliates=affiliates, keywords=keywords
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    """Страница авторизации."""
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("index"))
        else:
            flash("Неверное имя пользователя или пароль", "danger")

    return render_template("login.html", form=form)


def run_check_in_background(links):
    """Проверка в фоновом потоке."""
    global is_check_active

    get_screenshots(links)
    is_check_active = False

    # Тут будет вызов функции проверки скриншотов


def generate_urls(ZOOM):
    """Генерация списка ссылок."""
    base_url = "https://yandex.ru/maps/?"

    affiliates = [(a.longitude, a.latitude) for a in Affiliate.query.all()]
    keywords = [k.word for k in Keyword.query.all()]

    return [
        f"{base_url}{urllib.parse.urlencode({'ll': f'{lon},{lat}', 'z': zoom, 'text': keyword}, safe=',')}"
        for (lon, lat), keyword, zoom in product(affiliates, keywords, ZOOM)
    ]


@app.route("/start_check", methods=["POST"])
@login_required
def start_check():
    """Запуск проверки в фоновом потоке."""
    links = generate_urls(ZOOMS)
    threading.Thread(target=run_check_in_background, args=(links,)).start()
    flash("Проверка запущена", "success")

    return redirect(url_for("index"))


@app.route("/logout")
@login_required
def logout():
    """Функция для выхода пользователя."""
    logout_user()
    return redirect(url_for("login"))


def background_checker():
    """Проверка наличия параметра автоматической проверки."""
    global is_check_active

    while True:
        with app.app_context():
            client = Client.query.first()

            if client.auto_check and not is_check_active:
                links = generate_urls(ZOOMS)
                threading.Thread(target=run_check_in_background, args=(links,)).start()
                is_check_active = True

        time.sleep(client.check_frequency * 3600)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_initial_user()
    threading.Thread(target=background_checker, daemon=True).start()
    app.run(debug=False)
