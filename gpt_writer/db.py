import logging
import sqlite3
from icecream import ic


def init_users() -> None:
    ic('running in init_users')
    conn = sqlite3.connect('proj.db')
    cursor = conn.cursor()

    users_init = '''CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER,
    sessions_total INTEGER, 
    admin INTEGER, 
    tokens_per_session INTEGER
    );'''
    cursor.execute(users_init)
    conn.commit()
    cursor.close()
    logging.debug('users table initiated')


def init_sessions() -> None:
    ic('running in init_sessions')
    conn = sqlite3.connect('proj.db')
    cursor = conn.cursor()

    sessions_init = '''CREATE TABLE IF NOT EXISTS sessions(
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            session_id INTEGER,
            genre TEXT,
            setting TEXT,
            additional TEXT,
            chars TEXT
            );'''
    cursor.execute(sessions_init)
    conn.commit()
    cursor.close()
    logging.debug('sessions table initiated')


def init_prompts() -> None:
    ic('running in nit_prompts')
    conn = sqlite3.connect('proj.db')
    cursor = conn.cursor()

    prompts_init = '''CREATE TABLE IF NOT EXISTS prompts(
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    session_id INTEGER,
    role TEXT,
    text TEXT,
    tokens INTEGER
    );'''
    cursor.execute(prompts_init)
    conn.commit()
    cursor.close()
    logging.debug('prompts table initiated')


def get_uids() -> list[int]:
    ic('running in get_uids')
    """Возврщает все user_id, у которых есть активные сессии"""
    return [int(resp['user_id']) for resp in execute_select_query('SELECT DISTINCT user_id FROM sessions')]


def get_session_context(uid, sid):
    ic('running in get_session_context')
    """Возвращает роль, и текст каждого промпта с заданными session_id и user_id по порядку"""
    return execute_select_query('SELECT role, text FROM prompts where user_id = ? and session_id = ? ORDER BY id',
                                (uid, sid))


def insert_into_users(user_id, session_total, admin, tokens_per_session) -> None:
    ic('running in insert_into_users')
    conn = sqlite3.connect('proj.db')
    cursor = conn.cursor()
    sql = f'''INSERT 
                        INTO users (user_id, sessions_total, admin, tokens_per_session) 
                        VALUES (?, ?, ?, ?)'''
    cursor.execute(sql, (user_id, session_total, admin, tokens_per_session))
    conn.commit()
    cursor.close()
    logging.debug('insertion successful')


def insert_into_prompts(user_id, session_id, role, content, tokens) -> None:
    ic('running in insert_into_prompts')
    conn = sqlite3.connect('proj.db')
    cursor = conn.cursor()
    sql = f'''INSERT 
                INTO prompts (user_id, session_id, role, text, tokens) 
                VALUES (?, ?, ?, ?, ?)'''
    cursor.execute(sql, (user_id, session_id, role, content, tokens))
    conn.commit()
    cursor.close()
    logging.debug('insertion successful')


def insert_into_sessions(user_id, session_id) -> None:
    ic('running in insert_into_session')
    conn = sqlite3.connect('proj.db')
    cursor = conn.cursor()
    sql = f'''INSERT 
                INTO sessions (user_id, session_id)
                VALUES (?, ?)'''
    cursor.execute(sql, (user_id, session_id))
    conn.commit()
    conn.close()


def get_sessions(uid):
    ic('running in get_sessions')
    """Возвращает список из пар session_id: {genre: asdf, additional: asdf, setting: asdf, chars: asdf}"""
    response = execute_select_query('''SELECT 
                                                    session_id, genre, additional, setting, chars 
                                                FROM 
                                                    sessions 
                                                WHERE 
                                                    user_id = ?''', (uid,))
    if len(response) > 1:
        return [{resp['session_id']: [resp['genre'], resp['additional'], resp['setting'], resp['chars']]} for resp in response]
    else:
        return {
            response[0]['session_id']: [response[0]['genre'], response[0]['additional'], response[0]['setting'],
                                        response[0]['char']]
        } if response else {}


def remove_session_context(uid, sid) -> None:
    ic('running in remove_session_context')
    conn = sqlite3.connect('proj.db')
    cursor = conn.cursor()
    sql = 'DELETE FROM prompts WHERE user_id = ? AND session_id = ?'
    cursor.execute(sql, (uid, sid))
    conn.commit()
    conn.close()


def get_session_tokens(user_id: int):
    ic('running in get_session_tokens')
    """Возвращает токены, которые остались для использования в сессии"""
    res = execute_select_query('SELECT tokens FROM prompts WHERE user_id = ? ORDER BY id DESC LIMIT 1', (user_id,))
    return res[0]['tokens'] if res else 0


def update_sessions(uid, column, value, sid) -> None:
    ic('running in update_sessions')
    conn = sqlite3.connect('proj.db')
    cursor = conn.cursor()
    logging.debug('connected to proj.db successfully')
    sql = f'''UPDATE sessions  
                SET 
                    {column} = ?
                WHERE
                    user_id = ? AND session_id = ?'''  # знаю, что небезопасно,
    # но все равно column только я подставляю в коде
    cursor.execute(sql, (value, uid, sid))
    conn.commit()
    conn.close()


def update_users(uid, column, value) -> None:
    ic('running in update_users')
    conn = sqlite3.connect('proj.db')
    cursor = conn.cursor()
    logging.debug('connected to proj.db successfully')
    sql = f'''UPDATE users  
                SET 
                    {column} = ?
                WHERE
                    user_id = ?'''
    cursor.execute(sql, (value, uid))
    conn.commit()
    conn.close()


def execute_select_query(query, data=()) -> list[dict[int: list[str]]] | dict[int: list[str]]:
    ic('running in execute_select_query')
    """Выполняет запросы, которые направлены на получение информации из БД.
    Написал чтобы сократить размеры всех функций, которые берут разное
    Принимает сам запрос, и data(если нужно)"""
    conn = sqlite3.connect('proj.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    logging.debug('connected to proj.db successfully')
    if data:
        ret = [dict(res) for res in cursor.execute(query, data)]
        conn.commit()
        conn.close()
        return ret
    else:
        ret = [dict(res) for res in cursor.execute(query)]
        conn.commit()
        conn.close()
        return ret
