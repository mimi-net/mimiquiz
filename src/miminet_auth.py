from flask import flash, redirect, request, session, url_for
from flask_login import LoginManager, login_required
from werkzeug.security import generate_password_hash

from miminet_jwt import external_url_for
from miminet_model import User, db

# Global variables
UPLOAD_FOLDER = "static/avatar/"
UPLOAD_TMP_FOLDER = "static/tmp/avatar/"
ALLOWED_EXTENSIONS = {"bmp", "png", "jpg", "jpeg"}

login_manager = LoginManager()
login_manager.login_view = "login_index"

# create an alias of login_required decorator
login_required = login_required


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@login_manager.unauthorized_handler
def handle_needs_login():
    flash("Для выполнения этого действия необходимо войти.")
    return redirect(url_for("login_index", next=request.endpoint))


def redirect_next_url(fallback):
    if "next_url" not in session:
        redirect(fallback)
    try:
        dest_url = url_for(session["next_url"])
        return redirect(dest_url)
    except Exception:
        return redirect(fallback)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def redirect_login():
    return redirect(external_url_for("auth", filename="login.html", next=request.url))


def login_index():
    return redirect(external_url_for("auth", filename="login.html", next=request.url))


class TestUserData:
    """Data for test user initializing."""

    nick = "test_user"
    email = "selenium"
    password = "password"
    password_hash = generate_password_hash(password)


def insert_test_user(app):
    with app.app_context():
        try:
            test_user = User(
                nick=TestUserData.nick,
                email=TestUserData.email,
                password_hash=TestUserData.password_hash,
            )

            db.session.add(test_user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"An error occurred while adding the test user: {e}")


def remove_test_user(app):
    with app.app_context():
        try:
            user_to_remove = User.query.filter_by(email=TestUserData.email).first()

            if user_to_remove:
                db.session.delete(user_to_remove)
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"An error occurred while removing the test user: {e}")
