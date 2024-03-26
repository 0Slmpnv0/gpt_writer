import logging
import db
from gpt import User, users
from telebot.types import Message
from telebot import TeleBot
from dotenv import get_key
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from icecream import ic

logging.basicConfig(filename='bot.log', level=logging.DEBUG)
logging.debug('Bot startup initiated...')

tg_token = get_key(".env", 'TELEGRAM_BOT_TOKEN')
bot = TeleBot(tg_token)  # создание бота

db.init_sessions()
db.init_users()
db.init_prompts()  # создаю все нужные таблицы для проекта

basic_genres = ['Комедия', 'Хоррор', 'Триллер']
basic_chars = [
'''1. IT-специалист Макс
Максу 25 лет, и большую часть жизни он посвятил инженерии. В то время как остальные подростки засиживались допоздна, играя в Fortnite и PUBG, Макс увлекался робототехникой и программированием.
Сейчас это высокий стройный мужчина с короткими тёмными волосами. Он живёт в мегаполисе и работает в крупной IT-компании. В свободное время он любит посещать стендапы и заниматься виндсёрфингом. 
Макс — добрый и отзывчивый человек с отличным чувством юмора. Он умеет находить общий язык со всеми, будь то коллеги или случайные знакомые. Макс всегда готов прийти на помощь и не боится рисковать ради своих друзей.
''',
'''2. Юная эльфийка Эмилия
Эмилия — молодая эльфийка с длинными светлыми волосами, которые обрамляют её красивое лицо. Её большие зелёные глаза светятся мудростью и добротой. Она одета в лёгкое зелёное платье, которое подчёркивает её стройную фигуру и длинные ноги.
Юная эльфийка обладает магическими способностями и умеет управлять силами природы. По своей натуре она невероятно добрая и отзывчивая, готова всегда прийти на помощь к тем, кто в ней нуждается. Она также очень умна и всегда стремится узнать что-то новое. 
Эмилия мечтает найти своё место в мире и узнать больше о своих магических способностях!''',
'''3. Дружелюбная стримерша Лера
Лера — молодая девушка, известная в мире стримеров под ником ValeRun. У неё яркие голубые глаза, а улыбка всегда искренняя и тёплая. Длинные тёмные волосы она предпочитает подчёркивать утончённой и неброской одеждой в корейском стиле.
Благодаря своей привлекательности, жизнерадостному настрою и харизме она быстро набрала популярность в категориях косплея и «Just Chatting». 
За счёт прекрасного чувства юмора и заразительного смеха Леру часто приглашают быть ведущей крупных турниров по киберспорту. ''',
'''4. Виртуозный кот Маркус
Маркус — отважный и умный кот. Он родился с редким талантом к магии и со временем стал опытным волшебником. У этого рыжего пушистика сильное чувство справедливости и талант к игре на струнных инструментах.
Дерзкий темперамент, немного высокомерия и острый язык делают Маркуса идеальным героем для приключений. В них он встречает множество друзей и врагов, сражается со злом и раскрывает древние тайны. '''
]
# тут просто дефолтные персонажи от яндекса


MAX_USERS = 4
uids = db.get_uids()  # беру из БД все телеграмовские user_id, чтобы для каждого юзера создать объект класса User
for uid in uids:
    User(uid)  # в __init__ прописано автоматическое добавление в словарь users пары user_id: self
    sessions = db.get_sessions(uid)  # беру активные сессии, которые сохранены в БД
    if type(sessions) == list:  # не придумал как сделать лучше.
        # Если сессий несколько, то итерируюсь по ним и добавляю в self.active_sessions каждую.
        for session in sessions:
            if session:
                sid = list(session.keys())[0]
                genre, additional, setting, chars = list(session.values())[
                    0]  # get_sessions возвращает словари sid: {genre: asdf, additional: asdf, setting: asdf} ...],
                # или только один словарь
                users[uid].add_old_session(session_id=sid, genre=genre, setting=setting,
                                           additional=additional, tokens=db.get_session_tokens(uid), chars=chars)
                users[uid].active_sessions[sid].add_context(db.get_session_context(uid,
                                                                                   users[uid].active_sessions[
                                                                                       sid].session_id))
            else:
                continue
    else:  # Если сессия одна, то добавляю только ее
        sid = list(sessions.keys())[0]
        genre, additional, setting, chars = list(sessions.values())[0]
        users[uid].add_old_session(session_id=sid, genre=genre, setting=setting,
                                   additional=additional, tokens=db.get_session_tokens(uid), chars=chars)
        users[uid].active_sessions[sid].add_context(db.get_session_context(uid,
                                                                           users[uid].active_sessions[
                                                                               sid].session_id))


def build_reply_kb(buttons: list) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup()
    for button in buttons:
        kb.add(KeyboardButton(button))
    return kb


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message: Message):
    if message.text == '/start':
        text = ('Добро пожаловать в GPT-сценариста! Бот позволяет вам совместно с yaGPT lite '
                'писать сценарий на заданную вами тему. Всего вам будет доступно три сессии. '
                'Чтобы начать новую сессию используйте /new_story')
        if message.from_user.id not in users.keys():  # если пришел новый юзер, и лимит юзеров не исчерпан,
            # то и его добавляю в users
            if len(users) < MAX_USERS:
                User(message.from_user.id)
                db.insert_into_users(message.from_user.id, 0, 0, 1500)
                bot.send_message(message.from_user.id, text, reply_markup=build_reply_kb(['/new_story']))
            else:  # если исчерпан, то пользователь бесконечно попадает в looser, где его ждет одно и то же сообщение
                looser(message)
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


def looser(message: Message):
    bot.send_message(message.from_user.id, 'К сожалению, лимит пользователей бота исчерпан. '
                                           'Вы не можете отправлять запросы')
    bot.register_next_step_handler_by_chat_id(message.chat.id, looser)


@bot.message_handler(commands=['new_story', 'jump_to_active'])
def new_old_story(message: Message):
    if message.text == '/new_story':
        if users[message.from_user.id].add_new_session() == 'exc':
            bot.send_message(message.from_user.id, 'К сожалению, ваш лимит сессий исчерпан')
        else:
            db.insert_into_sessions(message.from_user.id, len(users[message.from_user.id].active_sessions))
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
            bot.send_message(message.from_user.id, 'Такой сессии нет. Пожалуйста, введите только ее номер без точки '
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
    bot.send_message(message.from_user.id, 'Отличный выбор! Теперь выберите, или напишите жанр:',
                     reply_markup=build_reply_kb(basic_genres))
    db.update_sessions(message.from_user.id, 'setting', message.text,
                       users[message.from_user.id].current_session.session_id)
    bot.register_next_step_handler_by_chat_id(message.chat.id, handle_genre)


def handle_genre(message: Message):
    users[message.from_user.id].current_session.genre = message.text
    bot.send_message(message.from_user.id, ('Прекрасно! Теперь выберите, или напишите персонажей'))
    db.update_sessions(message.from_user.id, 'genre', message.text,
                       users[message.from_user.id].current_session.session_id)
    bot.send_message(message.from_user.id, 'Вы хотите сами написать персонажей, или выбрать из готовых?',
                     reply_markup=build_reply_kb(['Готовые', 'Cвои']))
    bot.register_next_step_handler_by_chat_id(message.chat.id, handle_chars)


def handle_chars(message: Message):
    if message.text not in ['Готовые', 'Cвои']:
        bot.send_message(message.from_user.id, 'Просто тыкните на одну из кнопок',
                         reply_markup=build_reply_kb(['Готовые', 'Cвои']))
        bot.register_next_step_handler_by_chat_id(message.chat.id, handle_chars)
    elif message.text == 'Свои':
        bot.send_message(message.from_user.id, 'Отлично! Опишите всех своих персонажей в одном сообщении')
        bot.register_next_step_handler_by_chat_id(message.chat.id, handle_own_chars)
    elif message.text == 'Готовые':
        chars = "\n".join(basic_chars)
        bot.send_message(message.from_user.id, 'Напишите через запятую с пробелом цифры нужных персонажей:'
                                               f'Персонажи:'+'\n'+chars)
        bot.register_next_step_handler_by_chat_id(message.chat.id, handle_basic_chars)


def handle_basic_chars(message):  # если юзер хочет добавить наших персонажей
    chars = message.text.split(', ')
    available_chars = list(map(str, range(1, len(basic_chars)+1)))
    ic(available_chars)
    ic(chars)
    ic(all(x in available_chars for x in chars))
    if not all(x in available_chars for x in chars):
        bot.send_message(message.from_user.id, 'Таких вариантов ответа нет. Пожалуйста, введите через запятую '
                                               'с пробелом цифры нужных персонажей(пример: 1, 2, 3)')
        bot.register_next_step_handler_by_chat_id(message.chat.id, handle_basic_chars)
    else:
        for char in chars:
            users[message.from_user.id].current_session.chars += basic_chars[char - 1]
        db.update_sessions(message.from_user.id, 'chars', users[message.from_user.id].current_session.chars,
                           users[message.from_user.id].current_session.session_id)
        bot.send_message(message.from_user.id, ('Превосходно! Осталось только написать дополнительную информацию. '
                                                'Тут вы можете указать персонажей, которых хотели бы видеть в рассказе,'
                                                ' форму рассказа(стих? обычное повествование?), и так далее.'
                                                ' Можете попросить нейросеть не добавлять диалоги, '
                                                'или не добавлять своих персонажей. Главное - сделайте текст '
                                                'лаконичным.'
                                                ' Каждый токен на счету! Если вам больше нечего сказать, то ставьте -'))
        bot.register_next_step_handler_by_chat_id(message.chat.id, handle_additional)


def handle_own_chars(message: Message):  # если юзер хочет добавить своих персонажей
    users[message.from_user.id].current_session.chars = message.text
    db.update_sessions(message.from_user.id, 'chars', message.text,
                       users[message.from_user.id].current_session.session_id)
    bot.register_next_step_handler_by_chat_id(message.chat.id, handle_additional)


def handle_additional(message: Message):
    if message.text != '-':  # если доп инфа есть, то добавляем и ее
        users[message.from_user.id].current_session.additional = message.text
        db.update_sessions(message.from_user.id, 'additional', message.text,
                           users[message.from_user.id].current_session.session_id)
    bot.send_message(message.from_user.id, 'Теперь вы можете ввести начало истории')
    bot.register_next_step_handler_by_chat_id(message.chat.id, handle_story)


def handle_story(message: Message):  # отвечает за проверки всех команд, кроме /finish, отправку запросов в yaGPT
    if message.text in ['/start', '/help']:
        send_welcome(message)
    elif message.text in ['/new_session', '/jump_to_active']:
        new_old_story(message)
    elif message.text[0] == '/' and message.text not in ['/start', '/help', '/new_session', '/jump_to_active']:
        bot.send_message(message.chat.id, 'Сейчас вы не можете использовать эту команду')
        bot.register_next_step_handler_by_chat_id(message.chat.id, handle_continue)
    else:
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


def handle_continue(message: Message):  # добавил чтобы удобно хендлить /finish
    if message.text == '/finish':
        bot.send_message(message.from_user.id, 'Отправьте свою часть истории')
        bot.register_next_step_handler_by_chat_id(message.chat.id, handle_finish)
    else:
        handle_story(message)


def handle_finish(message: Message):  # Если юзер хочет закончить, то тут отвправляю в ask_gpt еще и resp_type
    resp = users[message.from_user.id].current_session.ask_gpt(message.text, 'завершить')
    match resp[0]:
        case 'exc1':
            logging.exception('Too small token amount for GPT resp')
            bot.send_message(message.from_user.id, resp[1])
            return
        case 'exc2':
            logging.exception('Too big user prompt')
            bot.send_message(message.from_user.id, resp[1] + '\nПопробуйте снова, но сократите размер своей части')
            bot.register_next_step_handler_by_chat_id(message.chat.id, handle_finish)
        case 'err':
            logging.error(f'Error: {resp[2]}')
        case 'succ':
            logging.info(f'Response successful')

    bot.send_message(message.from_user.id, resp[1])


bot.polling(non_stop=True)
