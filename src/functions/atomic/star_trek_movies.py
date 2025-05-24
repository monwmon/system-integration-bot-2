"""Модуль с функцией бота для поиска фильмов Star Trek через API stapi.co."""

import logging
import re
from datetime import datetime
from typing import List

import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData

from bot_func_abc import AtomicBotFunctionABC


class AtomicStarTrekBotFunction(AtomicBotFunctionABC):
    """Бот для поиска фильмов Star Trek через API stapi.co"""

    commands: List[str] = ["startrek", "stmovies"]
    authors: List[str] = ["monwmon"]
    about: str = "Поиск фильмов Star Trek"
    description: str = (
        "Доступные команды:\n"
        "/startrek или /stmovies - начать поиск фильмов Star Trek\n"
        "Позволяет получить список фильмов и информацию о каждом.\n"
        "Источник данных: stapi.co"
    )
    state: bool = True

    PAGE_SIZE = 5

    bot: telebot.TeleBot
    movie_keyboard_factory: CallbackData
    pagination_data = {}

    def set_handlers(self, bot: telebot.TeleBot):
        """Установка обработчиков сообщений и коллбэков"""
        self.bot = bot
        self.movie_keyboard_factory = CallbackData('movie_action', prefix=self.commands[0])

        @bot.message_handler(commands=self.commands)
        def startrek_handler(message: types.Message):
            msg = "Выберите действие с фильмами Star Trek:"
            bot.send_message(
                chat_id=message.chat.id,
                text=msg,
                reply_markup=self.__gen_markup()
            )

        @bot.callback_query_handler(func=None, config=self.movie_keyboard_factory.filter())
        def movie_callback(call: types.CallbackQuery):
            callback_data: dict = self.movie_keyboard_factory.parse(call.data)
            action = callback_data['movie_action']
            chat_id = call.message.chat.id

            if action == 'list':
                movies = self.__fetch_movies()
                if not movies:
                    bot.send_message(chat_id, "Фильмы не найдены.")
                    bot.answer_callback_query(call.id)
                    return
                self.pagination_data[chat_id] = {"movies": movies, "page": 0}
                self.__send_movies_page(chat_id=chat_id, page=0)

            elif action == 'info':
                force_reply = types.ForceReply(selective=False)
                msg = bot.send_message(
                    chat_id,
                    "Введите название фильма Star Trek:",
                    reply_markup=force_reply
                )
                bot.register_next_step_handler(msg, self.__process_movie_input)

            elif action.startswith("page_"):
                try:
                    page = int(action.split("_")[1])
                except ValueError:
                    bot.answer_callback_query(call.id, "Неверный номер страницы.")
                    return

                if chat_id not in self.pagination_data:
                    bot.answer_callback_query(call.id, "Данные устарели, повторите запрос.")
                    return

                self.pagination_data[chat_id]["page"] = page
                self.__send_movies_page(
                    chat_id=chat_id,
                    page=page,
                    edit_message=True,
                    message_id=call.message.message_id
                )

            bot.answer_callback_query(call.id)

    def __gen_markup(self):
        markup = types.InlineKeyboardMarkup(row_width=2)
        list_data = self.movie_keyboard_factory.new(movie_action="list")
        info_data = self.movie_keyboard_factory.new(movie_action="info")

        markup.add(
            types.InlineKeyboardButton("📃 Список фильмов", callback_data=list_data),
            types.InlineKeyboardButton("ℹ️ Информация о фильме", callback_data=info_data)
        )
        return markup

    def __fetch_movies(self) -> List[dict]:
        try:
            url = "https://stapi.co/api/v1/rest/movie/search"
            params = {"title": "Star Trek"}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('movies', [])
        except requests.exceptions.RequestException as e:
            logging.error("Star Trek API error: %s", e)
            return []

    def __send_movies_page(
        self,
        chat_id: int,
        page: int,
        *,
        edit_message: bool = False,
        message_id: int = None
    ):
        """Отправка страницы фильмов"""
        movies = self.pagination_data[chat_id]["movies"]
        page_size = self.PAGE_SIZE
        total = len(movies)
        start = page * page_size
        end = start + page_size
        page_movies = movies[start:end]

        text = "🎬 Фильмы Star Trek:\n\n"
        for movie in page_movies:
            director = movie['mainDirector']['name'] if movie.get('mainDirector') else 'N/A'
            text += (
                f"• {movie.get('title', 'N/A')} "
                f"({movie.get('yearFrom', 'N/A')}), реж. {director}\n"
            )
        text += f"\nСтраница {page + 1} из {(total + page_size - 1) // page_size}"

        markup = types.InlineKeyboardMarkup(row_width=2)
        if page > 0:
            back_data = self.movie_keyboard_factory.new(movie_action=f"page_{page - 1}")
            markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data=back_data))
        if end < total:
            next_data = self.movie_keyboard_factory.new(movie_action=f"page_{page + 1}")
            markup.add(types.InlineKeyboardButton("➡️ Вперёд", callback_data=next_data))

        if edit_message and message_id:
            self.bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=markup)
        else:
            self.bot.send_message(chat_id, text, reply_markup=markup)

    def get_all_movies(self) -> str:
        """Получает и форматирует список всех фильмов Star Trek."""
        movies = self.__fetch_movies()
        if not movies:
            return "Фильмы не найдены."

        film_list = "\n".join([
            f"• {movie.get('title', 'N/A')} ({movie.get('yearFrom', 'N/A')}), реж. "
            f"{movie['mainDirector']['name'] if movie.get('mainDirector') else 'N/A'}"
            for movie in movies
        ])
        return f"🎬 Фильмы Star Trek:\n{film_list}\n\n(Всего: {len(movies)})"

    def __format_date(self, date_str: str) -> str:
        """Преобразует дату YYYY-MM-DD в читаемый формат."""
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%-d %B %Y")
        except ValueError:
            return date_str

    def get_movie_info(self, title: str) -> str:
        """Получение подробной информации о фильме по названию."""
        try:
            title_clean = re.sub(r'\s*\(\d{4}\)\s*$', '', title).strip()

            url = "https://stapi.co/api/v1/rest/movie/search"
            params = {"title": title_clean}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            movies = data.get('movies', [])

            if not movies:
                return f"❌ Фильм '{title_clean}' не найден."

            movie = next(
                (m for m in movies if m.get('title', '').lower() == title_clean.lower()),
                movies[0]
            )

            lines = [f"🎬 {movie.get('title', 'N/A')}"]

            if movie.get('yearFrom') or movie.get('yearTo'):
                years = f"{movie.get('yearFrom') or ''}"
                if movie.get('yearTo') and movie.get('yearTo') != movie.get('yearFrom'):
                    years += f" - {movie.get('yearTo')}"
                lines.append(f"Годы: {years}")

            director = movie.get('mainDirector')
            if director and director.get('name'):
                lines.append(f"Режиссёр: {director['name']}")

            if movie.get('usReleaseDate'):
                readable_date = self.__format_date(movie['usReleaseDate'])
                lines.append(f"Дата выхода в США: {readable_date}")

            return "\n".join(lines)

        except requests.exceptions.RequestException as e:
            logging.error("Star Trek info error: %s", e)
            return "⚠️ Ошибка при получении информации о фильме."

    def __process_movie_input(self, message: types.Message):
        """Обработка пользовательского ввода названия фильма"""
        try:
            movie_title = message.text.strip()
            info = self.get_movie_info(movie_title)
            self.bot.send_message(chat_id=message.chat.id, text=info)
        except (ValueError, AttributeError, TypeError) as e:
            logging.error("Processing error: %s", e)
            self.bot.send_message(
                chat_id=message.chat.id,
                text=f"⚠️ Ошибка обработки запроса: {str(e)}"
            )
