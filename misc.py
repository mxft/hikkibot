from aiogram import types
from aiogram.types.inline_keyboard import InlineKeyboardButton, InlineKeyboardMarkup


class Misc:

    @staticmethod
    async def generate_approve_markup(message: types.Message) -> InlineKeyboardMarkup:
        approve_btn = InlineKeyboardButton(
            '✅',
            callback_data=f'approve:{message.message_id}:{message.from_user.id}'
        )
        deny_btn = InlineKeyboardButton(
            '❌',
            callback_data=f'deny:{message.message_id}:{message.from_user.id}'
        )
        return InlineKeyboardMarkup().add(approve_btn, deny_btn)

    @staticmethod
    async def generate_cancel_markup(message: types.Message) -> InlineKeyboardMarkup:
        cancel_btn = InlineKeyboardButton(
            'Отменить анкету',
            callback_data=f'cancel:{message.message_id}:{message.from_user.id}'
        )
        return InlineKeyboardMarkup().add(cancel_btn)

    @staticmethod
    async def generate_single_button(text: str, callback_data: str) -> InlineKeyboardMarkup:
        button = InlineKeyboardButton(text, callback_data=callback_data)
        return InlineKeyboardMarkup().add(button)
