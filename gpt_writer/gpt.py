import time
import requests
from dotenv import get_key
import logging
import db
from icecream import ic

folder_id = get_key('.env', 'FOLDER_ID')


def create_new_iam_token() -> dict[str: str]:
    """Возвращает метадату нового IAM"""
    metadata_url = "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token"
    headers = {"Metadata-Flavor": "Google"}
    response = requests.get(metadata_url, headers=headers)
    return response.json()


def check_iam() -> None:
    """Проверяет истек ли срок годности IAM токена. Если истек, то вызывает create_new_iam_token()"""
    global expires_at
    if expires_at < time.time():
        global iam
        iam_data = create_new_iam_token()
        iam = iam_data['access_token']
        expires_at = iam_data['expires_in']


token_data = create_new_iam_token()
iam = token_data['access_token']
expires_at = time.time() + token_data['expires_in']


class User:
    """Класс для удобной работы с юзерами"""
    def __init__(self, uid: int):
        global users
        self.uid = uid
        self.active_sessions: dict[int: Session] = {}
        self.total_sessions = 0
        self.current_session: Session | None = None
        users[uid] = self

    def add_old_session(self, genre, setting, additional, session_id, chars, tokens=1500):
        """Добавляет в self.active_sessions новый объект класса Session. """
        self.total_sessions += 1
        self.active_sessions[session_id] = Session(
            session_id=len(self.active_sessions) + 1,
            uid=self.uid,
            fid=folder_id,
            genre=genre,
            setting=setting,
            additional=additional,
            chars=chars,
            initial_tokens=tokens
        )

    def add_new_session(self):
        self.total_sessions += 1
        if self.total_sessions <= 3:
            db.update_users(self.uid, 'sessions_total', self.total_sessions)
            self.active_sessions[len(self.active_sessions) + 1] = Session(
                session_id=len(self.active_sessions) + 1,
                uid=self.uid,
                fid=folder_id)
        else:
            self.total_sessions -= 1
            logging.exception(f'Too many sessions for user {self.uid}')
            return 'exc'


users: dict[int: User] = {}


class Session:
    def __init__(self,
                 session_id: int,
                 uid: int,
                 fid: str,
                 initial_tokens: int = 1500,
                 max_model_resp_tokens: int = 200,
                 temperature: int = 1,
                 setting: str = '',
                 additional: str = '',
                 genre: str = '',
                 chars: str = ''
                 ):
        self.session_id: int = session_id
        self.uid: int = uid
        self.folder_id: str = fid
        self.context: list[dict[str: str]] = []
        self.temperature: int = temperature
        self.tokens: int = initial_tokens
        self.model_tokens: int = max_model_resp_tokens
        self.setting: str = setting
        self.additional: str = additional
        self.genre: str = genre
        self.chars: str = chars
        users[uid].current_session = self

    def add_context(self, context: list[dict[str: str]] | dict[str: str]):
        """Метод для добавления контекста сессии из БД"""
        if type(context) == list:
            self.context += context
        else:
            self.context.append(context)

    def count_tokens(self, text) -> int:
        """Метод для подсчитывания токенов"""
        ic(text)
        headers = {
            'Authorization': f'Bearer {iam}',
            'Content-Type': 'application/json'
        }
        data = {
            "modelUri": f"gpt://{folder_id}/yandexgpt/latest",
            "maxTokens": self.model_tokens,
            "text": text
        }
        ic(data)
        tokens = requests.post(
            "https://llm.api.cloud.yandex.net/foundationModels/v1/tokenize",
            json=data,
            headers=headers
        ).json()['tokens']
        ic(tokens)
        return len(tokens)

    def save_prompt(self, prompt):
        """Сохраняет промпт в БД и вычитает из доступных токенов токены для prompt"""
        self.tokens -= self.count_tokens(prompt['text'])
        db.insert_into_prompts(self.uid, self.session_id, prompt['role'], prompt['text'],
                               self.tokens)

    def ask_gpt(self, prompt, resp_type='продолжить') -> list[int]:
        """Запрос в gpt. Принимает зам запрос, и resp_type.
        resp_type нужен для того, чтобы правильно выбрать sys_prompt"""
        sys_prompts = {
            'продолжить': ('Ты - опытный сторителлер, и вместе с пользователем вы пишете рассказ. '
                           'Твоя задача - продолжать повествование за пользователем, не надо ничего добавлять в начале.'
                           ' Просто продолжай с того момента, где закончил пользователь. Ты можешь '
                           'добавлять персонажей и диалоги, если это уместно, и пользователь не просил об обратном\n'
                           f'Вот Пожелания пользователя: Жанр: {self.genre}\nСеттинг: {self.setting};'
                           f'\nПерсонажи: {self.chars}'),  # Возможно, упоротое решение, но я буду просто
            # сразу добавлять всех персонажей в одну строку с помощью \n
            'завершить': 'Заверши рассказ, который ты составил вместе с пользователем'
        }
        sys_prompt = sys_prompts[resp_type]
        ic(resp_type)
        ic(self.context)
        if self.additional:
            sys_prompt += f'\nТакже пользователь попросил учесть: {self.additional}'
        ic(self.context)
        context_prompt_size = ''.join([prompt['text'] for prompt in self.context])
        if not self.context or sys_prompt == 'завершить':
            self.tokens -= self.count_tokens(sys_prompt)
        if self.count_tokens(prompt + context_prompt_size) > self.tokens:
            ic(len(context_prompt_size))
            ic(self.context)
            if self.count_tokens(context_prompt_size) > self.tokens:
                self.harakiri()
                return ['exc1', 'Извините, ваш рассказ получился слишком длинным, чтобы его продолжить.'
                                ' Чтобы создать новый можете использовать /new_story']
            return ['exc2', (f'Извините, ваш запрос с учетом контекста слишком большой. '
                             f'У вас осталось {self.tokens - self.tokens} токенов, '
                             f'или примерно {(self.tokens - self.tokens) * 3} символов чтобы закончить')]
        self.tokens -= self.count_tokens(prompt + context_prompt_size)
        check_iam()
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
        self.context.append({'role': 'user', 'text': prompt})
        response = requests.post(
            'https://llm.api.cloud.yandex.net/foundationModels/v1/completion',
            headers=headers,
            json=json
        )
        if response.status_code != 200:
            logging.error(f'GPT error code: {response.status_code}')
            return ['err', f'Извините((. Произошла какая-то ошибка. Мы уже запомнили ее код и рано '
                           f'или поздно починим(нет). Код ошибки: {response.status_code}',
                    response.status_code]
        else:
            text = response.json()['result']['alternatives'][0]['message']['text']
            self.save_prompt({'role': 'assistant', 'text': text})
            self.context.append({'role': 'assistant', 'text': text})
            if resp_type == 'завершить':
                self.harakiri()
            return ['succ', text]

    def harakiri(self):
        """Совершает харакири(удаляет себя из активных сессий)"""
        db.remove_session_context(self.uid, self.session_id)
        ic(users[self.uid].active_sessions)
        users[self.uid].active_sessions.pop(self.session_id)
