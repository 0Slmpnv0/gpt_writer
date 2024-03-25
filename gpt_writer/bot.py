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
db.init_sessions()
db.init_users()
db.init_prompts()
uids = db.get_uids()
for uid in uids:
    User(uid)
    sessions = db.get_sessions_with_ids(uid)
    if type(sessions) == list:
        for session in sessions:
            if session:
                sid = list(session.keys())[0]
                genre, additional, setting = list(session.values())[0]
                users[uid].add_old_session(session_id=sid, genre=genre, setting=setting,
                                           additional=additional, tokens=db.get_session_tokens(uid))
                users[uid].active_sessions[sid].add_context(db.get_session_context(uid,
                                                                                   users[uid].active_sessions[
                                                                                       sid].session_id))
            else:
                continue
    else:
        sid = list(sessions.keys())[0]
        genre, additional, setting = list(sessions.values())[0]
        users[uid].add_old_session(session_id=sid, genre=genre, setting=setting,
                                   additional=additional, tokens=db.get_session_tokens(uid))
        users[uid].active_sessions[sid].add_context(db.get_session_context(uid,
                                                                           users[uid].active_sessions[
                                                                               sid].session_id))


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message: Message):
    if message.text == '/start':
        text = ('Добро пожаловать в GPT-сценариста! Бот позволяет вам совместно с yaGPT lite '
                'писать сценарий на заданную вами тему. Всего вам будет доступно три сессии. '
                'Чтобы начать новую сессию используйте /new_story')
        if message.from_user.id not in users.keys():
            User(message.from_user.id)
            bot.send_message(message.from_user.id, text, reply_markup=build_reply_kb(['/new_story']))
        else:
            repl = ['/new_story']
            if users[message.from_user.id].active_sessions:
                text = (
                    f'Бот обнаружил у вас {len(users[message.from_user.id].active_sessions)} активных сессий. Чтобы '
                    f'перейти к какой-либо из них, выберите /jump_to_active')
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
        if users[message.from_user.id].add_new_session() == 'exc':
            bot.send_message(message.from_user.id, 'К сожалению, ваш лимит сессий исчерпан')
        else:
            db.insert_data('sessions', message.from_user.id, len(users[message.from_user.id].active_sessions))
            bot.send_message(message.from_user.id, 'Сессия добавлена! Теперь выберите сеттинг')
            bot.register_next_step_handler_by_chat_id(message.chat.id, handle_setting)
    else:
        text = 'Выберите нужную сессию, введя ее номер'
        for session in users[message.from_user.id].active_sessions.values():
            text += f'\n{session.session_id}. жанр: {session.genre}, сеттинг: {session.setting}'
        bot.send_message(message.from_user.id, text,
                         reply_markup=build_reply_kb(
                             [session.session_id for session in users[message.from_user.id].active_sessions.values()]
                         ))
        bot.register_next_step_handler_by_chat_id(message.chat.id, handle_jumping)


def handle_jumping(message: Message):
    try:
        if int(message.text) not in [session.session_id for session in
                                     users[message.from_user.id].active_sessions.values()]:
            bot.send_message(message.from_user.id, 'Такой сесси нет. Пожалуйста, введите только ее номер без точки '
                                                   'Другие команды работать не будут',
                             reply_markup=build_reply_kb(
                                 [session.session_id for session in users[message.from_user.id].active_sessions]
                             ))
            bot.register_next_step_handler_by_chat_id(message.chat.id, handle_jumping)
        else:
            users[message.from_user.id].current_session = users[message.from_user.id].active_sessions[int(message.text)]
            if not users[message.from_user.id].current_session.setting:
                bot.send_message(message.from_user.id, 'Мы остановились на выборе сеттинга. '
                                                       'Пожалуйста, выберите сеттинг')
                bot.register_next_step_handler_by_chat_id(message.chat.id, handle_setting)
            elif not users[message.from_user.id].current_session.genre:
                bot.send_message(message.from_user.id, 'Мы остановились на выборе жанра. '
                                                       'Пожалуйста, выберите жанр')
                bot.register_next_step_handler_by_chat_id(message.chat.id, handle_genre)
            elif not users[message.from_user.id].current_session.additional:
                bot.send_message(message.from_user.id, 'Мы остановились на выборе дополнительной информации. '
                                                       'Пожалуйста, выберите ее')
                bot.register_next_step_handler_by_chat_id(message.chat.id, handle_additional)

            else:
                bot.send_message(message.from_user.id, 'Вы уже можете отправлять свою часть')
                bot.register_next_step_handler_by_chat_id(message.chat.id, handle_continue)

    except:
        bot.send_message(message.from_user.id, 'Такой сессии нет. Пожалуйста, введите только ее номер без точки. '
                                               'Другие команды работать не будут',
                         reply_markup=build_reply_kb(
                             [session.session_id for session in users[message.from_user.id].active_sessions.values()]
                         ))
        bot.register_next_step_handler_by_chat_id(message.chat.id, handle_jumping)


def handle_setting(message: Message):
    users[message.from_user.id].current_session.setting = message.text
    bot.send_message(message.from_user.id, 'Отличный выбор! Теперь выберите жанр')
    db.update_sessions(message.from_user.id, 'setting', message.text,
                       users[message.from_user.id].current_session.session_id)
    bot.register_next_step_handler_by_chat_id(message.chat.id, handle_genre)


def handle_genre(message: Message):
    users[message.from_user.id].current_session.genre = message.text
    bot.send_message(message.from_user.id, ('Превосходно! Осталось только написать дополнительную информацию. '
                                            'Тут вы можете указать персонажей, которых хотели бы видеть в рассказе, '
                                            'форму рассказа(стих? обычное повествование? решать вам.), и так далее. '
                                            'Можете попросить нейросеть не добавлять диалоги, '
                                            'или не добавлять своих персонажей. Главное - сделайте текст лаконичным. '
                                            'Каждый токен на счету! Если вам больше нечего сказать, то ставьте -'))
    db.update_sessions(message.from_user.id, 'genre', message.text,
                       users[message.from_user.id].current_session.session_id)
    bot.register_next_step_handler_by_chat_id(message.chat.id, handle_additional)


def handle_additional(message: Message):
    if message.text:
        users[message.from_user.id].current_session.additional = message.text
        db.update_sessions(message.from_user.id, 'additional', message.text,
                           users[message.from_user.id].current_session.session_id)
    bot.send_message(message.from_user.id, 'Теперь вы можете ввести начало истории')
    bot.register_next_step_handler_by_chat_id(message.chat.id, handle_story)


def handle_story(message: Message):
    users[message.from_user.id].current_session.save_prompt({'role': 'user', 'text': message.text})
    resp = users[message.from_user.id].current_session.ask_gpt(message.text)
    match resp[0]:
        case 'exc':
            logging.exception('Too big prompt')
            bot.register_next_step_handler_by_chat_id(message.chat.id, handle_story)
        case 'err':
            logging.error(f'Error: {resp[2]}')
        case 'succ':
            logging.info(f'Response successful')
    bot.send_message(message.from_user.id, resp[1])
    if resp[0] == 'succ':
        bot.register_next_step_handler_by_chat_id(message.chat.id, handle_continue)


def handle_continue(message: Message):
    if message.text == '/finish':
        bot.send_message(message.from_user.id, 'Отправьте свою часть истории')
        bot.register_next_step_handler_by_chat_id(message.chat.id, handle_finish)
    elif message.text[0] == '/':
        bot.send_message(message.chat.id, 'Сейчас вы не можете применять никакие команды кроме '
                                          '/finish чтобы нейросеть завершила рассказ после вашей части')
    else:
        handle_story(message)


def handle_finish(message: Message):
    resp = users[message.from_user.id].current_session.ask_gpt(message.text, 'завершить')
    match resp[0]:
        case 'exc1':
            logging.exception('Too small token amount for GPT resp')
            bot.send_message(message.from_user.id, resp[1])
            return
        case 'exc2':
            logging.exception('Too big user prompt')
            bot.send_message(message.from_user.id, resp[1]+'\nПопробуйте снова, но сократите размер своей части')
            bot.register_next_step_handler_by_chat_id(message.chat.id, handle_finish)
        case 'err':
            logging.error(f'Error: {resp[2]}')
            bot.register_next_step_handler_by_chat_id(message.chat.id)
        case 'succ':
            logging.info(f'Response successful')

    bot.send_message(message.from_user.id, resp[1])


bot.polling(non_stop=True)
