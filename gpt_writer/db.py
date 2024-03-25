import logging
import random
import sqlite3
from icecream import ic


def init_users():
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


def init_sessions():
    conn = sqlite3.connect('proj.db')
    cursor = conn.cursor()

    sessions_init = '''CREATE TABLE IF NOT EXISTS sessions(
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            session_id INTEGER,
            genre TEXT,
            setting TEXT,
            additional TEXT
            );'''
    cursor.execute(sessions_init)
    conn.commit()
    cursor.close()
    logging.debug('sessions table initiated')


def init_prompts():
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


def get_uids():
    return [resp['user_id'] for resp in execute_select_query('SELECT DISTINCT user_id FROM sessions')]


def get_session_context(uid, sid):
    return execute_select_query('SELECT role, text FROM prompts where user_id = ? and session_id = ? ORDER BY id',
                                (uid, sid))


def insert_data(table, *args):
    conn = sqlite3.connect('proj.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    logging.debug('connected to proj.db successfully')
    if table == 'prompts':
        sql = f'''INSERT 
                    INTO {table} (user_id, session_id, role, text, tokens) 
                    VALUES (?, ?, ?, ?, ?)'''
        user_id, session_id, role, content, tokens = args
        cursor.execute(sql, (user_id, session_id, role, content, tokens))
    elif table == 'users':
        sql = f'''INSERT 
                    INTO {table} (user_id, sessions_total, admin, tokens_per_session) 
                    VALUES (?, ?, ?, ?)'''
        user_id, session_total, admin, tokens_per_session = args
        cursor.execute(sql, (user_id, session_total, admin, tokens_per_session))

    else:
        sql = f'''INSERT 
                    INTO {table} (user_id, session_id)
                    VALUES (?, ?)'''
        user_id, session_id = args
        cursor.execute(sql, (user_id, session_id))
    conn.commit()
    cursor.close()
    logging.debug('insertion successful')


def execute_changing_query(query, data):
    conn = sqlite3.connect('proj.db')
    cursor = conn.cursor()
    logging.debug('connected to proj.db successfully')
    cursor.execute(query, data)
    conn.commit()
    cursor.close()


def get_sessions_with_ids(uid):
    response = execute_select_query('''SELECT 
                                                    session_id, genre, additional, setting 
                                                FROM 
                                                    sessions 
                                                WHERE 
                                                    user_id = ?''', (uid,))
    if len(response) > 1:
        return [{resp['session_id']: [resp['genre'], resp['additional'], resp['setting']]} for resp in response]
    else:
        return {
            response[0]['session_id']: [response[0]['genre'], response[0]['additional'], response[0]['setting']]
        } if response else {}


def remove_session_context(uid, sid):
    conn = sqlite3.connect('proj.db')
    cursor = conn.cursor()
    sql = 'DELETE FROM prompts WHERE user_id = ? AND session_id = ?'
    cursor.execute(sql, (uid, sid))


def get_session_tokens(user_id: int):
    res = execute_select_query('SELECT tokens FROM prompts WHERE user_id = ? ORDER BY id DESC LIMIT 1', (user_id,))
    return res[0]['tokens'] if res else 0


def update_sessions(uid, column, value, sid):
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


def update_users(uid, column, value):
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


def execute_select_query(query, data=()) -> list:
    conn = sqlite3.connect('proj.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    logging.debug('connected to proj.db successfully')
    if data:
        return [dict(res) for res in cursor.execute(query, data)]
    else:
        return [dict(res) for res in cursor.execute(query)]
