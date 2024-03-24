import logging

import db
from gpt import User, users
from telebot.types import Message
from telebot import TeleBot
from dotenv import get_key


tg_token = get_key(".env", 'TELEGRAM_BOT_TOKEN')
bot = TeleBot(tg_token)


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message: Message):
    if message.text == '/start':
        text = ('обро пожаловать в GPT-сценариста! Бот позволяет вам совместно с yaGPT lite '
                'писать сценарий на заданную вами тему. Всего вам будет доступно три сессии')
        if message.from_user.id not in users.keys:
            User(uid=message.from_user.id)
            text = 'Д' + text
        else:
            text = 'Снова д' + text  # может это и извращеие, но мне так нравится)
    else:
        text = ('Бот-сценарист помогает вам писать сценарии с помощью yaGPT. '
                'Вы по очереди пишете рассказ частями. Когда вам покажется, что пора заканчивать, '
                'выберите команду /end_story, а после напишите свою часть. '
                'То есть предпоследнюю, а GPT закончит рассказ')
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['new_story'])
def new_story(message: Message):
    if users[message.from_user.id].add_session() == 'exc':
        bot.send_message(message.from_user.id, 'К сожалению, ваш лимит сессий исчерпан')
    else:
        bot.send_message(message.from_user.id, 'Сессия добавлена! Теперь выберите сеттинг')
        bot.register_next_step_handler_by_chat_id(message.chat.id, handle_setting)


def handle_setting(message: Message):
    users[message.from_user.id].active_sessions[-1].setting = message.text
    bot.send_message(message.from_user.id, 'Отличный выбор! Теперь выберите жанр')
    bot.register_next_step_handler_by_chat_id(message.chat.id, handle_genre)


def handle_genre(message: Message):
    users[message.from_user.id].active_sessions[-1].genre = message.text
    bot.send_message(message.from_user.id, ('Превосходно! Осталось только написать дополнительную информацию. '
                                            'Тут вы можете указать персонажей, которых хотели бы видеть в рассказе, '
                                            'форму рассказа(стих? обычное повествование? решать вам.), и так далее. '
                                            'Можете попросить нейросеть не добавлять диалоги, '
                                            'или не добавлять своих персонажей. Главное - сделайте текст лаконичным. '
                                            'Каждый токен на счету!'))
    bot.register_next_step_handler_by_chat_id(message.chat.id, handle_additional)


def handle_additional(message: Message):
    users[message.from_user.id].active_sessions[-1].additional = message.text
    bot.send_message(message.from_user.id, 'Теперь вы можете ввести начало истории')


def handle_story(message: Message):
    users[message.from_user.id].current_session.save_prompt(message.text)
    resp = users[message.from_user.id].current_session.ask_gpt(message.text)
    match resp[0]:
        case 'exc':
            logging.exception('Too big prompt')
        case 'err':
            logging.error(f'Error: {resp[2]}')
        case 'succ':
            logging.info(f'Response successful')
    bot.send_message(message.from_user.id, resp[1])


def handle_continue(message: Message):
    if message.text == '/finish':
        bot.register_next_step_handler_by_chat_id(message.chat.id, handle_finish)
    elif message.text[0] == '/':
        bot.send_message(message.chat.id, 'Сейчас вы не можете применять никакие комманды кроме '
                                          '/finish чтобы нейросеть завершила рассказ после вашей части')
    else:
        handle_story(message)


def handle_finish(message: Message):
    resp = users[message.from_user.id].current_session.ask_gpt(message.text, 'завершить')
    match resp[0]:
        case 'exc':
            logging.exception('Too big prompt')
        case 'err':
            logging.error(f'Error: {resp[2]}')
        case 'succ':
            logging.info(f'Response successful')
    bot.send_message(message.from_user.id, resp[1])
