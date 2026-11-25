import hashlib
import os
import re
import uuid

from flask import Flask, jsonify, request
from flask_restx import Api
from werkzeug.middleware.proxy_fix import ProxyFix

from models.books import api as books_api
from models.statistic import api as stats_api

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config["RESTX_MASK_SWAGGER"] = False

VERIFY_TOKEN = "TUSUR-CHERMENIN-20261123-BA7B00FB"
VERIFY_DATE = "2026-11-08"
VERIFICATION_DATA = []

api = Api(
    app=app,
    version="1.0",
    title="Literature Catalog API",
    description="REST API для каталога литературных произведений с CRUD операциями и статистикой",
    doc="/",
)

api.add_namespace(books_api)
api.add_namespace(stats_api)


def normalize_text(text):
    """Приводит текст ответа к каноническому виду для SHA-256."""
    lines = [line.strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    lines = [re.sub(r"\s+", " ", line) for line in lines]
    return "\n".join(lines)


@app.after_request
def add_verify_hash(response):
    """Добавляет SHA-256 фактически возвращённого проверочного JSON-тела."""
    verification_path = (
        request.path == "/api/disease/"
        or re.fullmatch(r"/api/disease/[^/]+", request.path) is not None
    )
    if request.method == "GET" and response.status_code == 200 and verification_path:
        normalized = normalize_text(response.get_data(as_text=True))
        response.headers["X-Verify-Hash"] = hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest()
    return response


@app.route("/api/disease/", methods=["POST"])
def create_verification_record():
    """Создаёт проверочную запись с персональным токеном."""
    source = request.get_json(silent=True)
    required_fields = {
        "country",
        "disease",
        "date",
        "sick",
        "recovered",
        "deaths",
    }
    if not isinstance(source, dict) or not required_fields.issubset(source):
        return {"message": "Переданы не все обязательные поля"}, 400
    if source["disease"] != VERIFY_TOKEN:
        return {"message": "Поле disease должно содержать проверочный токен"}, 400
    if source["date"] != VERIFY_DATE:
        return {"message": f"Поле date должно быть равно {VERIFY_DATE}"}, 400

    record = {
        "id": uuid.uuid4().hex[:8],
        "country": source["country"],
        "disease": source["disease"],
        "date": source["date"],
        "sick": source["sick"],
        "recovered": source["recovered"],
        "deaths": source["deaths"],
    }
    VERIFICATION_DATA.append(record)
    return jsonify(record), 201


@app.route("/api/disease/", methods=["GET"])
def get_verification_record():
    """Возвращает последнюю созданную проверочную запись."""
    if not VERIFICATION_DATA:
        return {"message": "Проверочная запись не найдена"}, 404
    return jsonify(VERIFICATION_DATA[-1]), 200


@app.route("/api/disease/<string:record_id>", methods=["GET"])
def get_verification_record_by_id(record_id):
    """Возвращает проверочную запись по строковому идентификатору."""
    for record in VERIFICATION_DATA:
        if record["id"] == record_id:
            return jsonify(record), 200
    return {"message": "Проверочная запись не найдена"}, 404


@app.route("/health", methods=["GET"])
def health():
    """Возвращает состояние сервиса для проверки хостингом."""
    return {"status": "ok"}, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
