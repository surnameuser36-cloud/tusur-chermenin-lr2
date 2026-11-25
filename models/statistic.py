import numpy as np
from flask_restx import Namespace, Resource, fields
from data.data import active_books

# Определение пространства имён
api = Namespace("books_statistics", description="Статистика по литературным произведениям")

# Модель статистики
BOOK_STATISTIC_MODEL = api.model(
    "BookStatistic",
    {
        "min": fields.Float(required=True, description="Минимальное значение"),
        "max": fields.Float(required=True, description="Максимальное значение"),
        "mean": fields.Float(required=True, description="Среднее значение"),
        "median": fields.Float(description="Медианное значение"),
        "std_dev": fields.Float(description="Стандартное отклонение"),
        "count": fields.Integer(description="Количество элементов"),
    },
)


def calculate_statistics(field):
    """Вычисление статистики по числовому полю"""
    try:
        values = [
            float(book[field])
            for book in active_books()
            if book.get(field) is not None
        ]
        if not values:
            return {"error": f'Нет данных для поля "{field}"'}, 400

        arr = np.array(values, dtype=np.float64)
        return {
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "mean": float(np.mean(arr)),
            "median": float(np.median(arr)),
            "std_dev": float(np.std(arr)),
            "count": len(arr),
        }
    except Exception as e:
        return {"error": str(e)}, 500


# Статистика по ценам
@api.route("/of/price")
class StatisticOfPrice(Resource):
    @api.marshal_with(BOOK_STATISTIC_MODEL, envelope="statistics")
    def get(self):
        """Получить статистику по ценам книг"""
        return calculate_statistics("price")


# Статистика по количеству страниц
@api.route("/of/pages")
class StatisticOfPages(Resource):
    @api.marshal_with(BOOK_STATISTIC_MODEL, envelope="statistics")
    def get(self):
        """Получить статистику по количеству страниц"""
        return calculate_statistics("pages")


# Статистика по рейтингу
@api.route("/of/rating")
class StatisticOfRating(Resource):
    @api.marshal_with(BOOK_STATISTIC_MODEL, envelope="statistics")
    def get(self):
        """Получить статистику по рейтингу книг"""
        return calculate_statistics("rating")


# Статистика по году публикации
@api.route("/of/year")
class StatisticOfYear(Resource):
    @api.marshal_with(BOOK_STATISTIC_MODEL, envelope="statistics")
    def get(self):
        """Получить статистику по годам публикации"""
        return calculate_statistics("year")


# Распределение по жанрам
@api.route("/by/genre")
class StatisticByGenre(Resource):
    def get(self):
        """Получить распределение книг по жанрам"""
        genres = {}
        books = active_books()
        for book in books:
            genre = book.get("genre")
            if genre:
                genres[genre] = genres.get(genre, 0) + 1
        return {"genres": genres, "total": len(books)}


# Распределение по авторам
@api.route("/by/author")
class StatisticByAuthor(Resource):
    def get(self):
        """Получить распределение книг по авторам"""
        authors = {}
        books = active_books()
        for book in books:
            author = book.get("author")
            if author:
                authors[author] = authors.get(author, 0) + 1
        return {"authors": authors, "total": len(books)}


# Распределение по количеству томов
@api.route("/by/volumes")
class StatisticByVolumes(Resource):
    def get(self):
        """Получить распределение книг по количеству томов"""
        volumes = {}
        books = active_books()
        for book in books:
            vol_count = book.get("volumes")
            if vol_count is not None:
                key = f"{vol_count} том."
                volumes[key] = volumes.get(key, 0) + 1
        return {"volumes": volumes, "total": len(books)}


# Статистика цен по жанрам
@api.route("/price/by/genre")
class PriceStatisticByGenre(Resource):
    def get(self):
        """Получить статистику цен по жанрам"""
        genre_stats = {}

        for book in active_books():
            genre = book.get("genre")
            price = book.get("price")

            if genre and price is not None:
                if genre not in genre_stats:
                    genre_stats[genre] = []
                genre_stats[genre].append(price)

        result = {}
        for genre, prices in genre_stats.items():
            arr = np.array(prices, dtype=np.float64)
            result[genre] = {
                "min_price": float(np.min(arr)),
                "max_price": float(np.max(arr)),
                "avg_price": round(float(np.mean(arr)), 2),
                "book_count": len(prices),
            }

        return result


# Статистика страниц по жанрам
@api.route("/pages/by/genre")
class PagesStatisticByGenre(Resource):
    def get(self):
        """Получить статистику количества страниц по жанрам"""
        genre_stats = {}

        for book in active_books():
            genre = book.get("genre")
            pages = book.get("pages")

            if genre and pages is not None:
                if genre not in genre_stats:
                    genre_stats[genre] = []
                genre_stats[genre].append(pages)

        result = {}
        for genre, page_counts in genre_stats.items():
            arr = np.array(page_counts, dtype=np.float64)
            result[genre] = {
                "min_pages": float(np.min(arr)),
                "max_pages": float(np.max(arr)),
                "avg_pages": round(float(np.mean(arr)), 1),
                "book_count": len(page_counts),
            }

        return result


# Статистика доступности по авторам
@api.route("/availability/by/author")
class AvailabilityByAuthor(Resource):
    def get(self):
        """Получить статистику доступности книг по авторам"""
        availability = {}

        for book in active_books():
            author = book.get("author")
            is_available = book.get("available", False)

            if author:
                if author not in availability:
                    availability[author] = {"available": 0, "sold_out": 0}

                if is_available:
                    availability[author]["available"] += 1
                else:
                    availability[author]["sold_out"] += 1

        return availability


# Статистика классика/современная литература
@api.route("/classic/summary")
class ClassicSummary(Resource):
    def get(self):
        """Получить сводку по классической и современной литературе"""
        books = active_books()
        classics = [book for book in books if book.get("is_classic")]
        modern = [book for book in books if not book.get("is_classic")]

        result = {
            "classics": {
                "count": len(classics),
                "avg_price": (
                    round(np.mean([b["price"] for b in classics]), 2)
                    if classics
                    else 0
                ),
                "avg_pages": (
                    round(np.mean([b["pages"] for b in classics]), 1)
                    if classics
                    else 0
                ),
            },
            "modern": {
                "count": len(modern),
                "avg_price": (
                    round(np.mean([b["price"] for b in modern]), 2)
                    if modern
                    else 0
                ),
                "avg_pages": (
                    round(np.mean([b["pages"] for b in modern]), 1)
                    if modern
                    else 0
                ),
            },
        }
        return result


# Статистика цены за страницу по жанрам
@api.route("/price_per_page/by/genre")
class PricePerPageByGenre(Resource):
    def get(self):
        """Получить статистику цены за страницу по жанрам"""
        genre_stats = {}

        for book in active_books():
            genre = book.get("genre")
            price = book.get("price")
            pages = book.get("pages")

            if genre and price is not None and pages:
                price_per_page = price / pages
                if genre not in genre_stats:
                    genre_stats[genre] = []
                genre_stats[genre].append(price_per_page)

        result = {}
        for genre, prices in genre_stats.items():
            arr = np.array(prices, dtype=np.float64)
            result[genre] = {
                "min_price_per_page": round(float(np.min(arr)), 2),
                "max_price_per_page": round(float(np.max(arr)), 2),
                "avg_price_per_page": round(float(np.mean(arr)), 2),
                "book_count": len(prices),
            }

        return result
