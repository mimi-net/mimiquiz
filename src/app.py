import os
import sys
from datetime import datetime, timedelta

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, render_template_string
from flask_admin import Admin
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    verify_jwt_in_request,
)
from flask_migrate import Migrate

from miminet_admin import (
    AnswerView,
    CreateCheckTaskView,
    MiminetAdminIndexView,
    QuestionCategoryView,
    QuestionView,
    SectionView,
    SessionQuestionView,
    TestView,
)
from miminet_auth import (
    insert_test_user,
    login_index,
    login_manager,
    redirect_login,
    remove_test_user,
)
from miminet_config import SECRET_KEY
from miminet_jwt import external_url_for, is_api_request
from miminet_model import Network, User, db, init_db
from miminet_network import create_network, web_network, web_network_shared
from quiz.controller.image_controller import image_routes, upload_image_endpoint
from quiz.controller.question_controller import (
    create_question_endpoint,
    delete_question_endpoint,
    get_questions_by_section_endpoint,
)
from quiz.controller.quiz_session_controller import (
    answer_on_session_question_endpoint,
    check_network_task_endpoint,
    finish_old_session_endpoint,
    finish_session_endpoint,
    get_question_by_session_question_id_endpoint,
    get_result_by_session_guid_endpoint,
    get_session_question_json,
    session_result_endpoint,
    start_session_endpoint,
)
from quiz.controller.section_controller import get_sections_by_test_endpoint
from quiz.controller.test_controller import (
    get_all_tests_endpoint,
    get_test_endpoint,
    get_tests_by_owner_endpoint,
)
from quiz.entity.entity import (
    Answer,
    Question,
    QuestionCategory,
    Section,
    SessionQuestion,
    Test,
)
from quiz.util.dto import get_organization

app = Flask(
    __name__, static_url_path="", static_folder="static", template_folder="templates"
)

BASE_DOMAIN = os.environ.get("BASE_DOMAIN", None)

# Получаем режим работы из переменных окружения
MODE = os.getenv("MODE", "dev")

app.config.update(
    JWT_SECRET_KEY=os.environ.get("JWT_SECRET_KEY", "secret-key"),
    JWT_TOKEN_LOCATION=["cookies"],
    JWT_COOKIE_DOMAIN=f".{BASE_DOMAIN}" if BASE_DOMAIN else None,
    JWT_COOKIE_SECURE=False if MODE == "dev" else True,
    JWT_COOKIE_CSRF_PROTECT=False if MODE == "dev" else True,
    JWT_COOKIE_SAMESITE="Lax",
    JWT_ACCESS_TOKEN_EXPIRES=timedelta(
        hours=float(os.environ.get("ACCESS_TOKEN_EXPIRES", 1))
    ),
    JWT_REFRESH_TOKEN_EXPIRES=timedelta(
        hours=float(os.environ.get("REFRESH_TOKEN_EXPIRES", 2))
    ),
)

allowed_hosts_env = os.environ.get("ALLOWED_HOSTS", "")
allowed_hosts = []
if allowed_hosts_env:
    allowed_hosts = [item.strip() for item in allowed_hosts_env.split(",")]

print(f"Allowed Origins: {allowed_hosts}")
CORS(
    app,
    resources={
        r"/*": {
            "origins": allowed_hosts,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "supports_credentials": True,
            "max_age": 3600,
        }
    },
    intercept_exceptions=False,
)

# SQLAlchimy config
load_dotenv()

# Получаем режим работы из переменных окружения
MODE = os.getenv("MODE", "dev")
MAIN_URL = os.getenv("MAIN_URL")

PUBLIC_CONFIG_KEYS = [
    "EXTERNAL_BASE_URL",
]


def get_database_uri(mode):
    """
    Выбирает URI базы данных в зависимости от режима работы.

    Args:
        mode: Режим работы ('dev' или 'prod')

    Returns:
        str: URI для подключения к БД
    """
    if mode == "dev":
        # Локальный PostgreSQL контейнер для разработки
        POSTGRES_HOST = os.getenv("POSTGRES_HOST")
        POSTGRES_USER = os.getenv("POSTGRES_DEFAULT_USER")
        POSTGRES_PASSWORD = os.getenv("POSTGRES_DEFAULT_PASSWORD")
        POSTGRES_DB_NAME = os.getenv("POSTGRES_DATABASE_NAME")
        POSTGRES_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB_NAME}"

        print(f"[DB] Using local PostgreSQL: {POSTGRES_HOST}/{POSTGRES_DB_NAME}")
        return POSTGRES_URL
    elif mode == "prod":
        # Yandex Cloud PostgreSQL для продакшена
        POSTGRES_HOST = os.getenv("YANDEX_POSTGRES_HOST")
        POSTGRES_PORT = os.getenv("YANDEX_POSTGRES_PORT", "6432")
        POSTGRES_USER = os.getenv("YANDEX_POSTGRES_USER")
        POSTGRES_PASSWORD = os.getenv("YANDEX_POSTGRES_PASSWORD")
        POSTGRES_DB_NAME = os.getenv("YANDEX_POSTGRES_DB")
        POSTGRES_SSLMODE = os.getenv("YANDEX_POSTGRES_SSLMODE", "verify-full")
        POSTGRES_SSLROOTCERT = os.getenv(
            "YANDEX_POSTGRES_SSLROOTCERT", "/app/.postgresql/root.crt"
        )

        if not all([POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD]):
            raise ValueError(
                "Missing Yandex Cloud PostgreSQL credentials in environment variables"
            )

        POSTGRES_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB_NAME}?sslmode={POSTGRES_SSLMODE}&sslrootcert={POSTGRES_SSLROOTCERT}"

        print(
            f"[DB] Using Yandex Cloud PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB_NAME}"
        )
        return POSTGRES_URL
    else:
        raise ValueError(f"Unknown MODE: {mode}. Expected 'dev' or 'prod'")


app.config["SQLALCHEMY_DATABASE_URI"] = get_database_uri(MODE)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["SECRET_KEY"] = SECRET_KEY
app.config["SESSION_COOKIE_NAME"] = "mimi_session"

# Init Databases
db.init_app(app)

# Init Flask-Migrate
migrate = Migrate(app, db)

# Init LoginManager
login_manager.init_app(app)
jwt = JWTManager(app)

# Init Sitemap
zero_days_ago = (datetime.now()).date().isoformat()

# App add_url_rule
# Login
app.add_url_rule("/auth/login.html", methods=["GET", "POST"], view_func=login_index)

# Network
app.add_url_rule("/create_network", methods=["GET"], view_func=create_network)
app.add_url_rule("/web_network", methods=["GET"], view_func=web_network)
app.add_url_rule("/web_network_shared", methods=["GET"], view_func=web_network_shared)

# Quiz
app.add_url_rule("/test/owner", methods=["GET"], view_func=get_tests_by_owner_endpoint)
app.add_url_rule(
    "/", methods=["GET"], view_func=get_all_tests_endpoint
)  # Возврат должен быть на другой рут
app.add_url_rule("/test/get", methods=["GET"], view_func=get_test_endpoint)

app.add_url_rule(
    "/section/test/all", methods=["GET"], view_func=get_sections_by_test_endpoint
)

app.add_url_rule(
    "/question/create", methods=["POST"], view_func=create_question_endpoint
)

app.add_url_rule(
    "/question/delete", methods=["DELETE"], view_func=delete_question_endpoint
)

app.add_url_rule(
    "/question/all", methods=["GET"], view_func=get_questions_by_section_endpoint
)

app.add_url_rule(
    "/session/question/json", methods=["GET"], view_func=get_session_question_json
)

app.add_url_rule(
    "/session/start", methods=["POST"], view_func=start_session_endpoint  # action form
)
app.add_url_rule(
    "/session/question",
    methods=["GET"],
    view_func=get_question_by_session_question_id_endpoint,
)
app.add_url_rule(
    "/session/answer",
    methods=["POST"],
    view_func=answer_on_session_question_endpoint,
)

app.add_url_rule(
    "/session/check_network_task",
    methods=["POST"],
    view_func=check_network_task_endpoint,
)

app.add_url_rule("/session/finish", methods=["PUT"], view_func=finish_session_endpoint)
app.add_url_rule(
    "/session/finishold", methods=["PUT"], view_func=finish_old_session_endpoint
)
app.add_url_rule("/session/result", methods=["GET"], view_func=session_result_endpoint)
app.add_url_rule(
    "/user/session/result",
    methods=["GET"],
    view_func=get_result_by_session_guid_endpoint,
)
app.add_url_rule("/images/upload", methods=["POST"], view_func=upload_image_endpoint)

app.register_blueprint(image_routes)

# Init Flask-admin
admin = Admin(
    app,
    index_view=MiminetAdminIndexView(),
    name="Miminet Admin",
)


admin.add_view(TestView(Test, db.session, name="Тесты"))
admin.add_view(SectionView(Section, db.session, name="Разделы"))
admin.add_view(QuestionView(Question, db.session, name="Вопросы"))
admin.add_view(AnswerView(Answer, db.session, name="Ответы"))
admin.add_view(
    QuestionCategoryView(QuestionCategory, db.session, name="Категории вопросов")
)
admin.add_view(SessionQuestionView(SessionQuestion, db.session))
admin.add_view(
    CreateCheckTaskView(
        Network,
        db.session,
        name="Создать задачу проверки",
        endpoint="create_check_task",
    )
)


@app.context_processor
def utility_processor():
    return dict(external_url_for=external_url_for)


@app.context_processor
def inject_user():
    try:
        verify_jwt_in_request()
        current_user_id = get_jwt_identity()
        current_user = User.query.filter(User.id == current_user_id).first()
        return dict(
            current_user_id=current_user_id,
            is_authenticated=True,
            current_user=current_user,
        )
    except Exception:
        return dict(current_user_id=None, is_authenticated=False, current_user=None)


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    if is_api_request():
        return jsonify({"msg": "Token expired"}), 401
    else:
        return redirect_login()


@jwt.invalid_token_loader
def invalid_token_callback(error):
    if is_api_request():
        return jsonify({"msg": "Invalid token"}), 422
    else:
        return redirect_login()


@jwt.unauthorized_loader
def missing_token_callback(error):
    if is_api_request():
        return jsonify({"msg": "Missing token"}), 401
    else:
        return redirect_login()


@app.route("/config.js")
def confing_js():
    config = {key: os.getenv(key) for key in PUBLIC_CONFIG_KEYS if os.getenv(key, "")}

    js_content = render_template_string(
        open("templates/config.js", "r", encoding="utf-8").read(), **config
    )

    return Response(js_content, mimetype="application/javascript")


@app.route("/home")
@jwt_required()
def home():
    user_id = get_jwt_identity()
    networks = (
        Network.query.filter(Network.author_id == user_id)
        .filter(Network.is_task.is_(False))
        .order_by(Network.id.desc())
        .all()
    )
    org = get_organization()
    return render_template(
        "home.html",
        networks=networks,
        organization_logo_uri=org.logo_uri,
        organization_name=org.name,
    )


@app.route("/refresh_access", methods=["POST", "GET"])
@jwt_required(refresh=True)
def refresh_access():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    refresh_token = create_refresh_token(identity=identity)

    response = jsonify({"msg": "access token refreshed"})
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response


if __name__ == "__main__":
    init_db(app)

    if len(sys.argv) > 1:
        if sys.argv[1] == "dev":
            insert_test_user(app)
        elif sys.argv[1] == "prod":
            remove_test_user(app)
    else:
        app.run()
