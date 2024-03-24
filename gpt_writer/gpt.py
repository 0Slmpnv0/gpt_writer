import time
from conspiracy import iam
import requests
from dotenv import get_key
import logging
import db
from icecream import ic

token_data = iam
iam = token_data['access_token']
expires_at = time.time() + token_data['expires_in']
folder_id = get_key('.env', 'FOLDER_ID')


def create_new_iam_token():
    """This one should update IAM token, but now I just import it from conspiracy.py"""
    metadata_url = "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token"
    headers = {"Metadata-Flavor": "Google"}
    response = requests.get(metadata_url, headers=headers)
    return response.json()


def check_iam():
    """checks if IAM token is not expired yet, and if it is, function calls create_new_token()"""
    global expires_at
    if expires_at < time.time():
        global iam
        iam_data = create_new_iam_token()
        iam = iam_data['access_token']
        expires_at = iam_data['expires_in']


class User:
    def __init__(self, uid: int):
        global users
        self.uid = uid
        self.active_sessions: dict[int: Session] = {}
        self.total_sessions = 0
        self.current_session: Session | None = None
        users[uid] = self

    def add_old_session(self, genre, setting, additional, session_id):
        self.active_sessions[session_id] = Session(
                    session_id=len(self.active_sessions) + 1,
                    uid=self.uid,
                    fid=folder_id,
                    genre=genre,
                    setting=setting,
                    additional=additional
        )

    def add_new_session(self):
        self.total_sessions += 1
        if self.total_sessions <= 3:
            db.update(self.uid, 'users', 'sessions_total', self.total_sessions)
            self.active_sessions[len(self.active_sessions) + 1] = Session(
                    session_id=len(self.active_sessions) + 1,
                    uid=self.uid,
                    fid=folder_id)
        else:
            self.total_sessions -= 1
            logging.exception(f'Too many sessions for user {self.uid}')
            return 'exc'

    def add_tokens(self, tokens: int):
        tokens_per_session = round(tokens / len(self.active_sessions))
        for session in self.active_sessions.items():
            session.tokens += tokens_per_session
        db.execute_changing_query('''UPDATE users SET tokens_per_session = ? WHERE user_id = ?''',
                                  (1500+tokens_per_session, self.uid, ))


users: dict[int: User] = {}


class Session:
    def __init__(self,
                 session_id: int,
                 uid: int,
                 fid: str,
                 initial_tokens: int = 1500,
                 max_model_resp_tokens=200,
                 temperature=1,
                 setting='',
                 additional='',
                 genre=''
                 ):
        self.session_id = session_id
        self.uid = uid
        self.folder_id = fid
        self.context: list[dict[str: str]] = []
        self.temperature = temperature
        self.tokens = initial_tokens
        self.model_tokens = max_model_resp_tokens
        self.setting = setting
        self.additional = additional
        self.genre = genre
        users[uid].current_session = self

    def add_context(self, context: list[dict[str: str]] | dict[str: str]):
        if type(context) == list:
            self.context += context
        else:
            self.context.append(context)

    def count_tokens(self, text):
        current_tokens = db.get_session_tokens(self.uid)
        if not current_tokens:
            current_tokens = 0
        headers = {
            'Authorization': f'Bearer {iam}',
            'Content-Type': 'application/json'
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
            return len(tokens) + current_tokens
        return current_tokens

    def save_prompt(self, prompt):
        db.insert_data('prompts', self.uid, self.session_id, prompt['role'], prompt['content'],
                       self.count_tokens(prompt['content']))

    def ask_gpt(self, prompt, resp_type='продолжить'):
        sys_prompts = {
            'продолжить': ('Ты - опытный сторителлер, и вместе с пользователем вы пишете рассказ. Ты можешь '
                           'добавлять персонажей и диалоги, если это уместно, и пользователь не просил об обратном'
                           f'Вот Пожелания пользователя: Жанр: {self.genre}; Сеттинг: {self.setting};'),
            'завершить': 'Заверши рассказ, который ты составил вместе с пользователем'
        }
        sys_prompt = sys_prompts[resp_type]
        if self.additional:
            sys_prompt += f'Также пользователь попросил учесть: {self.additional}'
        ic(self.context)
        cont_prompt_size = ' '.join([list(prompt.values())[0] for prompt in self.context])
        if self.count_tokens(prompt + sys_prompt + cont_prompt_size) > self.tokens:
            return ['exc', (f'Извините, ваш запрос с учетом контекста слишком большой. '
                            f'У вас осталось {self.tokens - self.count_tokens("")} токенов, '
                            f'или примерно {(self.tokens - self.count_tokens('')) * 3} символов. Чтобы закончить')]
        # check_iam()
        headers = {
            'Authorization': f'Bearer {iam}',
            'Content-Type': 'application/json'
        }
        json = {
            "modelUri": f"gpt://{folder_id}/yandexgpt-lite",
            "completionOptions": {
                "stream": False,
                "temperature": 0.7,
                "maxTokens": self.model_tokens
            },
            "messages": [{"role": "system", "text": sys_prompts[resp_type]}] + self.context + [{'role': 'user',
                                                                                                'text': prompt}]
        }
        ic(json)
        response = requests.post(
            'https://llm.api.cloud.yandex.net/foundationModels/v1/completion',
            headers=headers,
            json=json
        )

        if response.status_code != 200:
            logging.error(f'GPT error code: {response.status_code}')
            return ['err', f'Извините((. Произошла какая-то ошибка. Мы уже запомнили ее код и рано '
                           f'или поздно починим(нет). Код ошибки: {response.status_code})',
                    response.status_code]
        else:
            text = response.json()['result']['alternatives'][0]['message']['text']
            self.save_prompt({'role': 'assistant', 'content': text})
            if resp_type == 'завершить':
                self.harakiri()
            return ['succ', text]

    def harakiri(self):
        db.remove_session_context(self.uid, self.session_id)
        users[self.uid].active_sessions.pop(self.session_id)
        users[self.uid].add_tokens(self.tokens)
