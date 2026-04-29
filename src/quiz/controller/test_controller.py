import json

from flask import abort, jsonify, make_response, render_template, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from miminet_model import User
from quiz.service.test_service import (
    create_test,
    delete_test,
    edit_test,
    get_all_tests_by_organization,
    get_deleted_tests_by_owner,
    get_retakeable_tests,
    get_test,
    get_tests_by_author_name,
    get_tests_by_owner,
    publish_or_unpublish_test,
)
from quiz.util.dto import get_organization
from quiz.util.encoder import UUIDEncoder


@jwt_required()
def create_test_endpoint():
    user_id = get_jwt_identity()
    user = User.query.filter(User.id == user_id).first()
    res_id = create_test(
        name=request.json["name"],
        description=request.json["description"],
        user=user,
        is_retakeable=request.json["is_retakeable"],
    )
    ret = {"message": "Тест добавлен", "id": res_id}

    return make_response(jsonify(ret), 201)


@jwt_required()
def get_test_endpoint():
    res = get_test(request.args["id"])
    if res[1] == 404:
        abort(404)

    return make_response(jsonify(res), res[0])


@jwt_required()
def get_tests_by_owner_endpoint():
    user_id = get_jwt_identity()
    user = User.query.filter(User.id == user_id).first()
    res = get_tests_by_owner(user)

    return make_response(
        json.dumps([obj.__dict__ for obj in res], cls=UUIDEncoder), 200
    )


@jwt_required()
def get_all_tests_endpoint():
    quizzes = get_all_tests_by_organization()
    org = get_organization()
    return make_response(
        render_template(
            "quiz/quizzes.html",
            quizzes=quizzes,
            organization_logo_uri=org.logo_uri,
            organization_name=org.name,
        ),
        200,
    )


@jwt_required()
def get_retakeable_tests_endpoint():
    tests = get_retakeable_tests()

    return make_response(tests, 200)


@jwt_required()
def get_deleted_tests_by_owner_endpoint():
    user_id = get_jwt_identity()
    user = User.query.filter(User.id == user_id).first()
    res = get_deleted_tests_by_owner(user)

    return make_response(
        json.dumps([obj.__dict__ for obj in res], cls=UUIDEncoder), 200
    )


@jwt_required()
def delete_test_endpoint():
    test_id = request.args["id"]
    user_id = get_jwt_identity()
    user = User.query.filter(User.id == user_id).first()
    deleted = delete_test(user, test_id)
    if deleted == 404:
        ret = {"message": "Тест не существует", "id": test_id}
    elif deleted == 403:
        ret = {"message": "Попытка удалить чужой тест", "id": test_id}
    elif deleted == 409:
        ret = {"message": "Попытка удалить удалённый тест", "id": test_id}
    else:
        ret = {"message": "Тест удалён", "id": test_id}

    return make_response(jsonify(ret), deleted)


@jwt_required()
def edit_test_endpoint():
    test_id = request.json["id"]
    user_id = get_jwt_identity()
    user = User.query.filter(User.id == user_id).first()
    edited = edit_test(
        user=user,
        name=request.json["name"],
        test_id=test_id,
        description=request.json["description"],
        is_retakeable=request.json["is_retakeable"],
    )
    if edited == 404:
        ret = {"message": "Тест не существует", "id": test_id}
    elif edited == 403:
        ret = {"message": "Попытка редактировать чужой тест", "id": test_id}
    else:
        ret = {"message": "Тест редактирован", "id": test_id}

    return make_response(jsonify(ret), edited)


@jwt_required()
def get_tests_by_author_name_endpoint():
    tests = get_tests_by_author_name(request.json["author_name"])

    return make_response(
        json.dumps([obj.__dict__ for obj in tests], cls=UUIDEncoder), 200
    )


@jwt_required()
def publish_or_unpublish_test_endpoint():
    is_to_publish = request.json["to_publish"]
    test_id = request.args["id"]
    user_id = get_jwt_identity()
    user = User.query.filter(User.id == user_id).first()
    published = publish_or_unpublish_test(
        user=user, test_id=test_id, is_to_publish=is_to_publish
    )
    if published == 404:
        ret = {"message": "Тест не существует", "id": test_id}
    elif published == 403:
        ret = {"message": "Попытка опубликовать чужой тест", "id": test_id}
    else:
        if is_to_publish:
            ret = {"message": "Тест опубликован", "id": test_id}
        else:
            ret = {"message": "Теперь тест невозможно пройти", "id": test_id}

    return make_response(jsonify(ret), published)
