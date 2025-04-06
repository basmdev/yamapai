import csv
import os
import shutil
import threading
import time
import urllib
from datetime import datetime
from itertools import product

from dotenv import load_dotenv

load_dotenv()

from flask import (Flask, abort, flash, redirect, render_template, request,
                   send_from_directory, url_for)
from flask_login import LoginManager, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

import config
from ai.yolo import analyze_images
from forms import LoginForm
from mail_send.sender import send_email
from models import Affiliate, Client, Keyword, User, db
from report_export.export import create_excel_report
from webdriver.driver import get_screenshots

app = Flask(__name__)
app.config["APPLICATION_ROOT"] = "/"
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER
app.config["SQLALCHEMY_DATABASE_URI"] = config.SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = config.SQLALCHEMY_TRACK_MODIFICATIONS
app.config["SERVER_NAME"] = config.SERVER_NAME
app.config["PREFERRED_URL_SCHEME"] = config.PREFERRED_URL_SCHEME


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


@app.template_filter("custom_time_format")
def custom_time_format(value):
    """Формат временной метки."""
    try:
        str_value = str(value)
        if len(str_value) != 10:
            return "Некорректный формат"

        hours = str_value[:2]
        minutes = str_value[2:4]
        day = str_value[4:6]
        month = str_value[6:8]
        year = str_value[8:10]

        formatted_time = f"{day}.{month}.{year}, {hours}:{minutes}"
        return formatted_time
    except Exception:
        return "Некорректный формат"


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


@app.route("/screenshots/bad_results/<filename>")
def serve_screenshot(filename):
    """Отдает файл из папки screenshots/bad_results"""
    screenshot_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "screenshots", "bad_results"
    )
    try:
        return send_from_directory(screenshot_folder, filename)
    except FileNotFoundError:
        abort(404)


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


def process_screenshot_folders():
    """Обрабатывает папки со скриншотами, обновляет записи в базе."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(base_dir, "screenshots")

    if not os.path.exists(base_path):
        print("Папка screenshots не найдена.")
        return

    with app.app_context():
        for folder_name in os.listdir(base_path):
            folder_path = os.path.join(base_path, folder_name)

            parts = folder_name.split("_")
            if len(parts) < 3:
                continue

            longitude, latitude, check_time = parts[0], parts[1], parts[2]

            result = analyze_images(folder_path)

            affiliate = (
                db.session.query(Affiliate)
                .filter_by(longitude=longitude, latitude=latitude)
                .first()
            )

            if affiliate:
                affiliate.check_time = check_time
                affiliate.result = "OK" if result else "Отсутствует POI"
                db.session.commit()
            else:
                print(f"Не найден филиал с координатами {longitude}, {latitude}")


def extract_screenshot_data():
    """Обработка данных о скриншоте и копирование в static."""
    with app.app_context():
        base_folder = os.path.dirname(os.path.abspath(__file__))
        folder_path = os.path.join(base_folder, "screenshots", "bad_results")
        static_folder = os.path.join(base_folder, "static", "screenshots")

        if not os.path.exists(folder_path):
            print(f"Папка не найдена: {folder_path}")
            return []

        if not os.path.exists(static_folder):
            os.makedirs(static_folder)

        files = os.listdir(folder_path)
        screenshot_data = []

        for file in files:
            if file.endswith(".png"):
                try:
                    longitude, latitude, keyword, zoom, time = file[:-4].split("_")
                except ValueError:
                    continue

                src_path = os.path.join(folder_path, file)
                dst_path = os.path.join(static_folder, file)

                shutil.copy(src_path, dst_path)

                screenshot_link = url_for("static", filename=f"screenshots/{file}")

                location = Affiliate.query.filter_by(
                    latitude=latitude, longitude=longitude
                ).first()

                if location:
                    address = location.address
                    screenshot_data.append(
                        {
                            "address": address,
                            "keyword": keyword,
                            "screenshot": screenshot_link,
                            "time": time,
                            "zoom": zoom,
                        }
                    )

        return screenshot_data


def clear_screenshots_folder():
    """Очистка папки со скриншотами."""
    screenshot_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "screenshots"
    )

    for root, dirs, files in os.walk(screenshot_folder, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))

    print(f"Папка {screenshot_folder} очищена.")


def clear_before_report():
    """Очистка данных в папках static/screenshots и reports перед формированием отчета."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    folders_to_clear = [
        os.path.join(base_dir, "static", "screenshots"),
        os.path.join(base_dir, "reports"),
    ]

    for folder in folders_to_clear:
        if not os.path.exists(folder):
            print(f"Папка {folder} не существует.")
            continue

        for root, dirs, files in os.walk(folder, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                shutil.rmtree(os.path.join(root, name))

        print(f"Папка {folder} очищена.")


def run_check_in_background(links):
    """Проверка в фоновом потоке."""
    global is_check_active

    get_screenshots(links)  # Получение скриншотов
    process_screenshot_folders()  # Обработка скриншотов и запись в БД
    clear_before_report()  # Очистка перед формированием отчета
    create_excel_report(
        extract_screenshot_data(), custom_time_format
    )  # Создание отчета в формате Excel

    reports_folder = os.path.join(os.getcwd(), "reports")
    files_in_reports = os.listdir(reports_folder)

    if files_in_reports:
        latest_file = max(
            files_in_reports,
            key=lambda f: os.path.getmtime(os.path.join(reports_folder, f)),
        )
        file_path = os.path.join(reports_folder, latest_file)
        send_email(file_path)  # Отправка письма
    else:
        print("Не обнаружено отчетов в папке.")

    clear_screenshots_folder()  # Очистка после работы

    is_check_active = False


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
    global is_check_active

    if is_check_active:
        flash("Проверка уже запущена", "warning")
        return redirect(url_for("index"))

    is_check_active = True
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

            if client and client.auto_check and not is_check_active:
                links = generate_urls(ZOOMS)
                threading.Thread(target=run_check_in_background, args=(links,)).start()
                is_check_active = True
        if client:
            time.sleep(client.check_frequency * 3600)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_initial_user()
    threading.Thread(target=background_checker, daemon=True).start()
    app.run(debug=False)
