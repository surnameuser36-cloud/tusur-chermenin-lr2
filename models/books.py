from datetime import datetime, timezone

from flask import request
from flask_restx import Namespace, Resource, fields

from data.data import active_books, books_data, deleted_books

# Определение пространства имён
api = Namespace("books_catalog", description="API каталога литературных произведений")

# Модель книги
BOOK_MODEL = api.model(
    "Book",
    {
        "id": fields.Integer(required=True, description="Идентификатор книги"),
        "title": fields.String(required=True, description="Название произведения"),
        "genre": fields.String(required=True, description="Жанр произведения"),
        "price": fields.Float(required=True, description="Цена книги (руб.)"),
        "description": fields.String(description="Описание произведения"),
        "pages": fields.Integer(description="Количество страниц"),
        "year": fields.Integer(description="Год публикации"),
        "chapters": fields.Integer(description="Количество глав"),
        "volumes": fields.Integer(description="Количество томов"),
        "rating": fields.Float(description="Рейтинг книги (0.0 - 5.0)"),
        "author": fields.String(description="Автор произведения"),
        "available": fields.Boolean(description="Доступна для покупки"),
        "is_classic": fields.Boolean(description="Классическое произведение"),
        "has_illustrations": fields.Boolean(description="Есть иллюстрации"),
        "is_deleted": fields.Boolean(
            readonly=True, description="Признак мягкого удаления"
        ),
        "deleted_at": fields.String(
            readonly=True, description="Дата и время мягкого удаления"
        ),
    },
)


def find_book(book_id, include_deleted=False):
    """Находит книгу по ID и при необходимости учитывает удалённые записи."""
    for book in books_data:
        if book["id"] == book_id:
            if book.get("is_deleted") and not include_deleted:
                api.abort(404, "Книга с таким ID удалена")
            return book
    api.abort(404, "Книга с таким ID не найдена")


# Вывод всех книг
@api.route("/list/all")
class ListAllBooks(Resource):
    @api.doc(params={"include_deleted": "Добавить мягко удалённые записи"})
    @api.marshal_list_with(BOOK_MODEL, envelope="books")
    def get(self):
        """Получить список активных книг или всех книг"""
        include_deleted = request.args.get("include_deleted", "false").lower()
        if include_deleted in {"true", "1", "yes"}:
            return books_data
        return active_books()


@api.route("/list/deleted")
class ListDeletedBooks(Resource):
    @api.marshal_list_with(BOOK_MODEL, envelope="books")
    def get(self):
        """Получить список мягко удалённых книг"""
        return deleted_books()


# Универсальная сортировка по полю
def create_sort_route(field_name):
    @api.route(f"/list/all/sortBy/{field_name}")
    class ListAllSort(Resource):
        @api.marshal_list_with(BOOK_MODEL, envelope="books")
        def get(self):
            """Сортировка книг по указанному полю"""
            return sorted(
                active_books(),
                key=lambda x: (
                    x.get(field_name) if x.get(field_name) is not None else ""
                ),
            )


# Создание маршрутов сортировки
for field in [
    "id",
    "title",
    "genre",
    "price",
    "pages",
    "year",
    "chapters",
    "rating",
]:
    create_sort_route(field)


# Получение книги по ID
@api.route("/book/getBy/id/<int:book_id>")
class BookGetById(Resource):
    @api.marshal_with(BOOK_MODEL, envelope="book")
    def get(self, book_id):
        """Получить книгу по ID"""
        return find_book(book_id)


# Удаление книги по ID
@api.route("/book/deleteBy/id/<int:book_id>")
class BookDeleteById(Resource):
    @api.doc(params={"confirm": "Для подтверждения удаления передайте true"})
    @api.response(400, "Удаление не подтверждено")
    @api.response(409, "Книга уже удалена")
    @api.marshal_with(BOOK_MODEL, envelope="book")
    def delete(self, book_id):
        """Подтверждённо пометить книгу как удалённую"""
        confirmed = request.args.get("confirm", "false").lower()
        if confirmed not in {"true", "1", "yes"}:
            api.abort(400, "Удаление требует параметр confirm=true")

        book = find_book(book_id, include_deleted=True)
        if book.get("is_deleted"):
            api.abort(409, "Книга уже удалена")
        book["is_deleted"] = True
        book["deleted_at"] = datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        )
        return book


# Редактирование всех данных книги
@api.route("/book/editBy/id/all")
class BookEditByIdAll(Resource):
    @api.expect(BOOK_MODEL)
    @api.marshal_with(BOOK_MODEL, envelope="book")
    def put(self):
        """Редактировать все данные книги"""
        payload = api.payload
        book = find_book(payload["id"])
        values = dict(payload)
        for field_name in ("is_deleted", "deleted_at"):
            values.pop(field_name, None)
        book.update(values)
        return book


# Редактирование цены книги
@api.route("/book/editBy/id/price")
class BookEditByIdPrice(Resource):
    @api.expect(
        api.model(
            "PriceEdit",
            {
                "id": fields.Integer(required=True, description="ID книги"),
                "price": fields.Float(required=True, description="Новая цена"),
            },
        )
    )
    @api.marshal_with(BOOK_MODEL, envelope="book")
    def patch(self):
        """Редактировать цену книги"""
        book = find_book(api.payload["id"])
        book["price"] = api.payload["price"]
        return book


# Редактирование доступности
@api.route("/book/editBy/id/available")
class BookEditByIdAvailable(Resource):
    @api.expect(
        api.model(
            "AvailableEdit",
            {
                "id": fields.Integer(required=True, description="ID книги"),
                "available": fields.Boolean(
                    required=True, description="Доступна для покупки"
                ),
            },
        )
    )
    @api.marshal_with(BOOK_MODEL, envelope="book")
    def patch(self):
        """Редактировать статус доступности книги"""
        book = find_book(api.payload["id"])
        book["available"] = api.payload["available"]
        return book


# Добавление новой книги
@api.route("/book/add")
class BookAdd(Resource):
    @api.expect(BOOK_MODEL)
    @api.marshal_with(BOOK_MODEL, envelope="book")
    def post(self):
        """Добавить новую книгу"""
        payload = dict(api.payload)
        if any(book["id"] == payload["id"] for book in books_data):
            api.abort(409, "Книга с таким ID уже существует")
        payload["is_deleted"] = False
        payload["deleted_at"] = None
        books_data.append(payload)
        return payload


# Фильтрация по названию
@api.route("/list/title/<string:title>")
class ListByTitle(Resource):
    @api.marshal_list_with(BOOK_MODEL, envelope="books")
    def get(self, title):
        """Получить книги по названию (частичное совпадение)"""
        filtered = [
            b for b in active_books() if title.lower() in b["title"].lower()
        ]
        if not filtered:
            api.abort(404, f"Книги с названием '{title}' не найдены")
        return filtered


# Фильтрация по жанру
@api.route("/list/genre/<string:genre>")
class ListByGenre(Resource):
    @api.marshal_list_with(BOOK_MODEL, envelope="books")
    def get(self, genre):
        """Получить книги по жанру"""
        filtered = [
            b
            for b in active_books()
            if b.get("genre", "").lower() == genre.lower()
        ]
        if not filtered:
            api.abort(404, f"Книги жанра '{genre}' не найдены")
        return filtered


# Фильтрация по автору
@api.route("/list/author/<string:author>")
class ListByAuthor(Resource):
    @api.marshal_list_with(BOOK_MODEL, envelope="books")
    def get(self, author):
        """Получить книги по автору"""
        filtered = [
            b
            for b in active_books()
            if b.get("author", "").lower() == author.lower()
        ]
        if not filtered:
            api.abort(404, f"Книги автора '{author}' не найдены")
        return filtered


# Фильтрация классика/современная
@api.route("/list/is_classic/<string:is_classic>")
class ListByClassic(Resource):
    @api.marshal_list_with(BOOK_MODEL, envelope="books")
    def get(self, is_classic):
        """Получить книги по типу (классика/современная: true/false)"""
        is_classic_book = is_classic.lower() == "true"
        filtered = [
            b for b in active_books() if b.get("is_classic") == is_classic_book
        ]
        return filtered


# Фильтрация по году публикации
@api.route("/list/year/<int:year>")
class ListByYear(Resource):
    @api.marshal_list_with(BOOK_MODEL, envelope="books")
    def get(self, year):
        """Получить книги по году публикации"""
        filtered = [b for b in active_books() if b.get("year") == year]
        if not filtered:
            api.abort(404, f"Книги {year} года не найдены")
        return filtered


# Фильтрация по доступности
@api.route("/list/available")
class ListAvailable(Resource):
    @api.marshal_list_with(BOOK_MODEL, envelope="books")
    def get(self):
        """Получить только доступные книги"""
        return [b for b in active_books() if b.get("available")]
