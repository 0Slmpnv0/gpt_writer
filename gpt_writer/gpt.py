import time
from conspiracy import iam
import requests
from dotenv import get_key
import logging
import db

token_data = iam
iam = token_data['access_token']
expires_at = time.time() + token_data['expires_in']
folder_id = get_key('.env', 'FOLDER_ID')


def create_new_token():
    """This one should update IAM token, but now I just import it from conspiracy.py"""
    metadata_url = "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token"
    headers = {"Metadata-Flavor": "Google"}
    response = requests.get(metadata_url, headers=headers)
    return response.json()


def check_iam():
    """checks if IAM token is now expired yet, and if it is, function calls create_new_token()"""
    global expires_at
    if expires_at < time.time():
        global iam
        iam = create_new_token()['access_token']


class User:
    def __init__(self, uid):
        global users
        self.uid = uid
        self.sessions: list[Session] = []
        users.update({uid: self})

    def add_session(self):
        if db.get_sessions_quantity(self.uid):
            self.sessions.append(
                Session(
                    session_id=len(self.sessions) + 1,
                    uid=self.uid,
                    fid=folder_id,
                ))

    def add_tokens(self, tokens: int):
        tokens_per_session = tokens / len(self.sessions) - 1
        for session in self.sessions:
            session.increase_tokens(tokens_per_session)


users: dict[int: User] = {}


class Session:
    def __init__(self,
                 session_id: int,
                 uid: int,
                 fid: str,
                 initial_tokens: int = 1500,
                 max_model_resp_tokens=100,
                 temperature=1):
        super().__init__(uid)
        self.session_id = session_id
        self.uid = uid
        self.folder_id = fid
        self.context: list[dict[str: str | int]] = []
        self.temperature = temperature
        self.tokens = initial_tokens
        self.model_tokens = max_model_resp_tokens
        self.setting = ''
        self.additional = ''
        self.genre = ''

    def increase_tokens(self, tokens):
        self.tokens += tokens

    def count_tokens(self, text):
        current_tokens = db.get_session_tokens(self.uid)
        headers = {
            "Authorization': f'Bearer {iam}",
            "Content-Type': 'application/json"
        }
        data = {
            "modelUri": f"gpt://{folder_id}/yandexgpt/latest",
            "maxTokens": self.model_tokens,
            "text": text
        }
        if text:
            tokens = requests.post(
                "https://llm.api.cloud.yandex.net/foundationModels/v1/tokenize",
                json=data,
                headers=headers
            ).json()['tokens']
            return tokens + current_tokens
        return current_tokens

    def add_prompt(self, prompt):
        db.insert_data(self.uid, self.session_id, prompt['role'], prompt['content'],
                       self.count_tokens(prompt['content']))

    def ask_gpt(self, prompt, resp_type=''):
        sys_prompts = {
            'продолжить': 'Вместе с пользователем вы пишете историю с персонажами: '
        }
        if self.count_tokens(prompt) < self.tokens:
            return ['exc', (f'Извините, ваш запрос с учетом контекста слишком большой. '
                            f'У вас осталось {self.tokens - self.count_tokens("")}, '
                            f'или примерно {(self.tokens - self.count_tokens('')) * 3} символов. Чтобы закончить')]

    def harakiri(self):
        users[self.uid].add_tokens(self.tokens)
        users[self.uid].sessions.remove(self)
