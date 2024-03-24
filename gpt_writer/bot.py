from icecream import ic
import logging
import db
from gpt import User, users
from utils import build_reply_kb
from telebot.types import Message
from telebot import TeleBot
from dotenv import get_key


logging.basicConfig(filename='bot.log', level=logging.DEBUG)
logging.debug('Bot startup initiated...')
tg_token = get_key(".env", 'TELEGRAM_BOT_TOKEN')
bot = TeleBot(tg_token)
uids = db.get_uids()
print(uids)
for uid in uids:
    User(uid)
    sessions = [db.get_sessions(uid)]
    for session in sessions:
        ic(users)
        ic(sessions)
        users[uid].add_session()
        users[uid].active_sessions[-1].session_id = session
        ic()
        users[uid].active_sessions[-1].add_context(db.get_session_context(uid,
                                                                          users[uid].active_sessions[-1].session_id))


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message: Message):
    if message.text == '/start':
        text = ('Добро пожаловать в GPT-сценариста! Бот позволяет вам совместно с yaGPT lite '
                'писать сценарий на заданную вами тему. Всего вам будет доступно три сессии. '
                'Чтобы начать новую сессию используйте /new_sroty')
        if message.from_user.id not in users.keys():
            ic(users)
            User(message.from_user.id)
            db.insert_data('users', message.from_user.id, 0, 0, 1500)
            bot.send_message(message.from_user.id, text, reply_markup=build_reply_kb(['/new_story']))
        else:
            repl = ['/new_story']
            if users[message.from_user.id].active_sessions:
                text = (f'Бот обнаружил у вас {len(users[message.from_user.id].active_sessions)} активных сессий. Чтобы'
                        f'Перейти к какой-либо из них, выберите /jump_to_active')
                repl += ['/jump_to_active']
            bot.send_message(message.from_user.id, text, reply_markup=build_reply_kb(repl))


    else:
        text = ('Бот-сценарист помогает вам писать сценарии с помощью yaGPT. '
                'Вы по очереди пишете рассказ частями. Когда вам покажется, что пора заканчивать, '
                'выберите команду /end_story, а после напишите свою часть. '
                'То есть предпоследнюю, а GPT закончит рассказ')
        bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['new_story', 'jump_to_active'])
def new_story(message: Message):
    if message.text == '/new_story':
        if users[message.from_user.id].add_session() == 'exc':
            bot.send_message(message.from_user.id, 'К сожалению, ваш лимит сессий исчерпан')
        else:
            bot.send_message(message.from_user.id, 'Сессия добавлена! Теперь выберите сеттинг')
            bot.register_next_step_handler_by_chat_id(message.chat.id, handle_setting)
    else:
        text = 'Выберите нужную сессию, введя ее номер'
        for session in users[message.from_user.id].active_sessions:
            text += f'\n{session.session_id}. жанр: {session.genre}, сеттинг: {session.setting}'
        bot.send_message(message.from_user.id, text,
                         reply_markup=build_reply_kb(
                             [session.session_id for session in users[message.from_user.id].active_sessions]
                         ))


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
    bot.register_next_step_handler_by_chat_id(message.chat.id, handle_story)


def handle_story(message: Message):
    users[message.from_user.id].current_session.save_prompt({'role': 'user', 'content': message.text})
    resp = users[message.from_user.id].current_session.ask_gpt(message.text)
    match resp[0]:
        case 'exc':
            logging.exception('Too big prompt')
        case 'err':
            logging.error(f'Error: {resp[2]}')
        case 'succ':
            logging.info(f'Response successful')
    bot.send_message(message.from_user.id, resp[1])
    bot.register_next_step_handler_by_chat_id(message.chat.id, handle_continue)


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


bot.polling(non_stop=True)
