import logging
import random
import sqlite3
from icecream import ic


def init_sessions():
    conn = sqlite3.connect('proj.db')
    cursor = conn.cursor()

    users_init = '''CREATE TABLE IF NOT EXISTS sessions(
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            session_id INTEGER,
            genre TEXT,
            setting TEXT,
            additional TEXT
            );'''
    cursor.execute(users_init)
    conn.commit()
    cursor.close()
    logging.debug('sessions table initiated')


def init_users():
    conn = sqlite3.connect('proj.db')
    cursor = conn.cursor()

    users_init = '''CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        sessions_total INTEGER,
        admin INTEGER,
        tokens_per_session INTEGER
        );'''
    cursor.execute(users_init)
    conn.commit()
    cursor.close()
    logging.debug('users table initiated')


def init_prompts():
    conn = sqlite3.connect('proj.db')
    cursor = conn.cursor()

    prompts_init = '''CREATE TABLE IF NOT EXISTS prompts(
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    session_id INTEGER,
    role TEXT,
    content TEXT,
    tokens INTEGER
    );'''
    cursor.execute(prompts_init)
    conn.commit()
    cursor.close()
    logging.debug('prompts table initiated')


def get_uids():
    return [resp['user_id'] for resp in execute_select_query('SELECT DISTINCT user_id FROM prompts')]


def get_session_context(uid, sid):
    return execute_select_query('SELECT role, content FROM prompts where user_id = ? and session_id = ? ORDER BY id',
                                (uid, sid))


def insert_data(table, *args):
    conn = sqlite3.connect('proj.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    logging.debug('connected to proj.db successfully')
    if table == 'prompts':
        sql = '''INSERT 
                    INTO ? (user_id, session_id, role, content, tokens) 
                    VALUES (?, ?, ?, ?, ?)'''
        user_id, session_id, role, content, tokens = args
        cursor.execute(sql, (table, user_id, session_id, role, content, tokens))
    elif table == 'users':
        sql = '''INSERT 
                    INTO ? (user_id, sessions_total, admin, tokens_per_session) 
                    VALUES (?, ?, ?, ?)'''
        user_id, session_total, admin, tokens_per_session = args
        cursor.execute(sql, (table, user_id, session_total, admin, tokens_per_session))

    else:
        sql = '''INSERT 
                    INTO ? (user_id, session_id)
                    VALUES (?, ?)'''
        user_id, session_id, setting, genre, additional = args
        cursor.execute(sql, (user_id, session_id))
    conn.commit()
    cursor.close()
    logging.debug('insertion successful')


def execute_changing_query(query, data):
    conn = sqlite3.connect('proj.db')
    cursor = conn.cursor()
    logging.debug('connected to proj.db successfully')
    cursor.execute(query, data)


def get_user_data(user_id: int):
    res = execute_select_query('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return res if res else []


def get_sessions(uid):
    response = execute_select_query('SELECT DISTINCT session_id FROM prompts WHERE user_id = ?', (uid,))
    ic(response)
    if len(response) > 1:
        return [resp['session_id'] for resp in response]
    else:
        return response[0]['session_id']


def remove_session_context(uid, sid):
    conn = sqlite3.connect('proj.db')
    cursor = conn.cursor()
    sql = 'DELETE FROM prompts WHERE user_id = ? AND session_id = ?'
    cursor.execute(sql, (uid, sid))


def get_session_tokens(user_id: int):
    res = execute_select_query('SELECT tokens FROM prompts WHERE user_id = ? ORDER BY id DESC LIMIT 1', (user_id,))


def update(uid, table, column, value):
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    logging.debug('connected to users.db successfully')
    sql = '''UPDATE ?
                SET 
                    ? = ?
                WHERE
                    user_id = ?'''
    cursor.execute(sql, (column, value, uid))
    conn.commit()
    conn.close()


def execute_select_query(query, data=()) -> list:
    conn = sqlite3.connect('proj.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    logging.debug('connected to proj.db successfully')
    ic(query)
    ic(data)
    if data:
        ic([dict(res) for res in cursor.execute(query, data)])
        return [dict(res) for res in cursor.execute(query, data)]
    else:
        ic([dict(res) for res in cursor.execute(query)])
        return [dict(res) for res in cursor.execute(query)]
