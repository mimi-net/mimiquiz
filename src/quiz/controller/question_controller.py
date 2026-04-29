import json

from flask import abort, jsonify, make_response, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from miminet_model import User
from quiz.facade.question_facade import create_question, delete_question
from quiz.service.question_service import get_questions_by_section
from quiz.util.encoder import UUIDEncoder


@jwt_required()
def get_questions_by_section_endpoint():
    res = get_questions_by_section(request.args["id"])
    if res[1] == 404 or res[1] == 403:
        abort(res[1])

    return make_response(
        json.dumps([obj.__dict__ for obj in res[0]], cls=UUIDEncoder, default=str),
        res[1],
    )


@jwt_required()
def create_question_endpoint():
    user_id = get_jwt_identity()
    user = User.query.filter(User.id == user_id).first()
    section_id = request.args.get("id", None)
    res = create_question(section_id, request.json, user)
    if res[1] == 404 and "message" in res[0]:
        msg = res[0]["message"]
        ret = {"message": f"{msg}"}
    elif res[1] == 404:
        ret = {"message": "Не существует данного раздела", "id": section_id}
    elif res[1] == 403:
        ret = {"message": "Нельзя создать вопрос по чужому разделу", "id": section_id}
    elif res[1] == 400 and "missing" in res[0]:
        ret = {"message": "Некоторые изображения отсутствуют", "details": res[0]}
    elif res[1] == 400 and "message" in res[0]:
        ret = {
            "message": "Ваши требования не удовлетворяют шаблону.",
            "details": res[0],
        }
    elif res[1] == 400:
        ret = {
            "message": "Нельзя создать вопрос с данными параметрами в данном разделе",
            "id": section_id,
        }
    else:
        ret = {"message": "Вопрос создан", "id": res[0]}

    return make_response(jsonify(ret), res[1])


@jwt_required()
def delete_question_endpoint():
    question_id = request.args["id"]

    user_id = get_jwt_identity()
    user = User.query.filter(User.id == user_id).first()
    res = delete_question(request.args["id"], user)
    if res == 404:
        ret = {"message": "Вопрос не существует", "id": question_id}
    elif res == 403:
        ret = {
            "message": "Попытка удалить чужой вопрос или нет прав",
            "id": question_id,
        }
    elif res == 409:
        ret = {"message": "Попытка удалить удалённый вопрос", "id": question_id}
    else:
        ret = {"message": "Вопрос удалён", "id": question_id}

    return make_response(jsonify(ret), res)
