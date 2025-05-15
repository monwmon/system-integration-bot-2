import logging
from typing import List
import telebot
import requests
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC

class AtomicStarTrekBotFunction(AtomicBotFunctionABC):
    """Бот для поиска фильмов Star Trek через API stapi.co"""

    commands: List[str] = ["startrek", "stmovies"]
    authors: List[str] = ["YourName"]
    about: str = "Поиск фильмов Star Trek"
    description: str = (
        "Доступные команды:\n"
        "/startrek или /stmovies - начать поиск фильмов Star Trek\n"
        "Позволяет получить список фильмов и информацию о каждом.\n"
        "Источник данных: stapi.co"
    )
    state: bool = True

    bot: telebot.TeleBot
    movie_keyboard_factory: CallbackData

    def set_handlers(self, bot: telebot.TeleBot):
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

            if action == 'list':
                movies = self.get_all_movies()
                bot.send_message(call.message.chat.id, movies)
            elif action == 'info':
                force_reply = types.ForceReply(selective=False)
                msg = bot.send_message(
                    call.message.chat.id,
                    "Введите название фильма Star Trek:",
                    reply_markup=force_reply
                )
                bot.register_next_step_handler(msg, self.__process_movie_input)
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

    def get_all_movies(self) -> str:
        """Получить список всех фильмов Star Trek"""
        try:
            url = "https://stapi.co/api/v1/rest/film/search"  # пример API, надо уточнить точный эндпоинт
            # Используем фильтр для Star Trek (пример, может понадобиться уточнение)
            params = {"title": "Star Trek"}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            films = data.get('films', []) if 'films' in data else data.get('entities', [])
            if not films:
                return "Фильмы не найдены."

            film_list = "\n".join([f"• {film['title']}" for film in films])
            return f"🎬 Фильмы Star Trek:\n{film_list}\n\n(Всего: {len(films)})"
        except requests.exceptions.RequestException as e:
            logging.error(f"Star Trek API error: {e}")
            return "⚠️ Ошибка при получении списка фильмов."

    def get_movie_info(self, title: str) -> str:
        """Получить подробную информацию о фильме по названию"""
        try:
            url = "https://stapi.co/api/v1/rest/film/search"
            params = {"title": title}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            films = data.get('films', []) if 'films' in data else data.get('entities', [])

            if not films:
                return f"❌ Фильм '{title}' не найден."

            film = films[0]  # берем первый результат
            info = (
                f"🎬 {film.get('title', 'N/A')}\n"
                f"Год выпуска: {film.get('releaseDate', 'N/A')}\n"
                f"Описание: {film.get('description', 'Информация отсутствует')}\n"
                f"Режиссер: {film.get('director', 'N/A')}\n"
            )
            return info
        except requests.exceptions.RequestException as e:
            logging.error(f"Star Trek info error: {e}")
            return "⚠️ Ошибка при получении информации о фильме."

    def __process_movie_input(self, message: types.Message):
        try:
            movie_title = message.text.strip()
            info = self.get_movie_info(movie_title)
            self.bot.send_message(
                chat_id=message.chat.id,
                text=info
            )
        except Exception as e:
            logging.error(f"Processing error: {e}")
            self.bot.send_message(
                chat_id=message.chat.id,
                text=f"⚠️ Ошибка обработки запроса: {str(e)}"
            )