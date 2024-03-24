import logging
import sqlite3


def init_users():
    conn = sqlite3.connect('prompts.db')
    cursor = conn.cursor()

    users_init = '''CREATE TABLE IF NOT EXISTS prompts(
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    session_id INTEGER,
    role TEXT,
    content TEXT,
    tokens INTEGER
    );'''
    cursor.execute(users_init)
    conn.commit()
    cursor.close()
    logging.debug('prompts db initiated')


def insert_data(user_id: int, session_id: int, role: str, content: str, tokens: int):
    conn = sqlite3.connect('prompts.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    logging.debug('connected to users.db successfully')
    sql = '''INSERT 
            INTO prompts (user_id, session_id, role, content, tokens) 
            VALUES (?, ?, ?, ?, ?)'''
    cursor.execute(sql, (user_id, session_id, role, content, tokens))
    conn.commit()
    cursor.close()
    logging.debug('insertion successful')


def get_user_data(user_id: int):
    res = execute_query('SELECT * FROM prompts WHERE user_id = ?', (user_id, ))
    return res if res else []


def get_session_tokens(user_id: int):
    res = execute_query('SELECT tokens FROM prompts WHERE user_id = ? ORDER BY id DESC LIMIT 1', (user_id, ))


def execute_query(query, data=()):
    conn = sqlite3.connect('prompts.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    logging.debug('connected to users.db successfully')
    if data:
        return [dict(res) for res in cursor.execute(query, data)]
    else:
        return [dict(res) for res in cursor.execute(query)]
