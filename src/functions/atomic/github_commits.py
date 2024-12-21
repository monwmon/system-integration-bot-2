""""""

import os
import requests
from typing import List
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC

class GithubCommitsFunction(AtomicBotFunctionABC):
    """"""

    commands: List[str] = ["github", "gh"]
    authors: List[str] = ["IHVH"]
    about: str = "Получение коммитов репозитория"
    description: str = """В поле  *description* поместите подробную информацию о работе функции.
    Описание способов использования, логики работы. Примеры вызова функции - /ebf 
    Возможные параметры функции `/example`  """
    state: bool = True

    bot: telebot.TeleBot
    example_keyboard_factory: CallbackData

    def set_handlers(self, bot: telebot.TeleBot):

        @bot.message_handler(commands=self.commands)
        def github_message_hendler(message: types.Message):
            arr = message.text.split()

            token = os.environ.get("GITHUBTOKEN")
            owner = 'IHVH'
            repo = 'system-integration-bot-2'
            url = f'https://api.github.com/repos/{owner}/{repo}/commits/master'

            params = {'Authorization': f'Bearer {token}'}

            response = requests.get(url, headers=params)

            r = response.json()

            if(len(arr) > 1):
                bot.send_message(text=f'{arr[1]}', chat_id=message.chat.id)
            else:
                bot.send_message(text=response.text, chat_id=message.chat.id)
