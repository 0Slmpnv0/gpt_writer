from telebot.types import ReplyKeyboardMarkup, KeyboardButton


def build_reply_kb(buttons: list) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup()
    for button in buttons:
        kb.add(KeyboardButton(button))
    return kb
