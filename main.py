from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.exceptions import BadRequest, RetryAfter, TelegramAPIError, Unauthorized

from rights import Rights
from user import User
from misc import Misc

import sqlite3
from time import sleep

class HikkiBot:

    def __init__(self, token: str, channel: int):
        self.CHANNEL_ID = channel
        self.bot = Bot(token=token)
        self.dp = Dispatcher(self.bot, storage=MemoryStorage())
        self.rights = Rights()
        self.operators: dict = self.rights.operators
        self.db = sqlite3.connect('hikkibot.db')
        self.cursor = self.db.cursor()
        self.cursor.execute('CREATE TABLE IF NOT EXISTS waiting_pool (user_id INT, message_id INT, form TEXT)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS sent_messages (op_id INT, op_message_id INT, user_id INT)')
        self.db.commit()

    def setup_handlers(self):

        @self.dp.message_handler(commands=['start', 'help', 'rules'])
        async def send_help(message: types.Message):
            if not await self.dp.throttle('help', user_id=message.from_user.id, no_error=True):
                return

            if message.text == '/rules':
                msg = open('rules.txt', 'r', encoding='UTF-8').read()
            else:
                msg = open('howto.txt', 'r', encoding='UTF-8').read()
            await self.bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        
        @self.dp.message_handler(commands=['donate'])
        async def send_donate(message: types.Message):
            if not await self.dp.throttle('donate', user_id=message.from_user.id, no_error=True):
                return
            
            await self.bot.send_message(message.chat.id,
                                        open('donate.txt', 'r', encoding='UTF-8').read(),
                                        parse_mode="Markdown")

        @self.dp.message_handler(lambda m: not m.text.startswith('/'))
        async def get_form_request(message: types.Message):
            if not await self.dp.throttle('form', user_id=message.from_user.id, no_error=True):
                return

            document_exists = self.cursor.execute('SELECT * FROM waiting_pool WHERE user_id = ?',
                                                 (message.from_user.id,)).fetchone()
            if document_exists:
                self.cursor.execute('DELETE FROM waiting_pool WHERE user_id = ?', (message.from_user.id,))

            self.cursor.execute('INSERT INTO waiting_pool VALUES (?, ?, ?)', 
                               (message.from_user.id, message.message_id, message.text))

            keyboard = await Misc.generate_approve_markup(message)
            active_operators = [i for i in self.operators['operators'] 
                                if i not in self.rights.offline_operators]
            if active_operators:
                for op_id in active_operators:
                    sent_message = await self.bot.send_message(
                        op_id,
                        message.text,
                        reply_markup=keyboard
                    )
                    # TODO: remove from waiting pool after inserting into sent_messages,
                    # refactor all the code accordingly
                    self.cursor.execute('INSERT INTO sent_messages VALUES (?, ?, ?)',
                                       (op_id, sent_message.message_id, message.from_user.id))
            else:
                self.rights.waiting_messages.append(
                    {
                        'message': message,
                        'reply_markup': keyboard
                    }
                )
            kb_markup = await Misc.generate_cancel_markup(message)
            await message.reply('Ваша анкета принята на проверку.', reply_markup=kb_markup)

        @self.dp.message_handler(commands=['getid'])
        async def get_user_id(message: types.Message):
            await message.reply(message.from_user.id)

        @self.dp.message_handler(self.rights.operator_checker,
                                 commands=['online', 'offline'])
        async def set_op_status(message: types.Message):
            if message.text == '/online':
                self.rights.offline_operators.remove(message.from_user.id)
                await self.send_waiting_messages()
            else:
                self.rights.offline_operators.add(message.from_user.id)
            await message.reply('Done!')

        @self.dp.message_handler(self.rights.admin_checker, commands=['op', 'deop'])
        async def add_operator(message: types.Message):
            args = message.get_args().split()

            if len(args) == 1:
                if message.get_command() == '/op':
                    User(args[0]).op()
                    msg_text = f'Пользователь {args[0]} теперь оператор.'
                elif message.get_command() == '/deop':
                    User(args[0]).deop()          
                    msg_text = f'Пользователь {args[0]} больше не оператор.'      
                await message.reply(msg_text)
            else:
                await message.reply('Неверные аргументы!')

        @self.dp.callback_query_handler(lambda query: query.data.startswith('approve'))
        async def approve_handler(query: types.CallbackQuery):
            _, message_id, personal_chat_id = query.data.split(':')
            document_exists = self.cursor.execute('SELECT * FROM waiting_pool WHERE user_id = ?', 
                                                 (personal_chat_id,)).fetchone()
            if not document_exists:
                await query.answer('Анкеты уже не существует.')
                return

            dm_msg_text = 'Анкета опубликована.'
            button_text = 'Одобрено ☑️'
            await self.bot.copy_message(self.CHANNEL_ID,
                                        personal_chat_id, message_id)
            await self.bot.send_message(
                personal_chat_id,
                dm_msg_text,
                reply_to_message_id=message_id
            )

            keyboard = await Misc.generate_single_button(button_text, 'blank')

            for op_id, op_msg_id, _ in self.cursor.execute('SELECT * FROM sent_messages WHERE user_id = ?',
                                                          (personal_chat_id,)).fetchall():
                    await self.bot.edit_message_reply_markup(op_id, op_msg_id, reply_markup=keyboard)
                    self.cursor.execute('DELETE FROM sent_messages WHERE op_message_id = ?', (op_msg_id,))

        @self.dp.callback_query_handler(lambda query: query.data.startswith('deny'))
        async def deny_handler(query: types.CallbackQuery):
            _, message_id, personal_chat_id = query.data.split(':')
            document_exists = self.cursor.execute('SELECT * FROM waiting_pool WHERE user_id = ?',
                                                 (personal_chat_id,)).fetchone()
            if not document_exists:
                await query.answer('Анкеты уже не существует.')
                return

            dm_msg_text = 'Анкета отклонена.'
            button_text = 'Отклонено ❌'
            await self.bot.send_message(
                personal_chat_id,
                dm_msg_text,
                reply_to_message_id=message_id
            )
            keyboard = await Misc.generate_single_button(button_text, 'blank')
            for op_id, op_msg_id, _ in self.cursor.execute('SELECT * FROM sent_messages WHERE user_id = ?',
                                                          (personal_chat_id,)).fetchall():
                await self.bot.edit_message_reply_markup(op_id, op_msg_id, reply_markup=keyboard)
                self.cursor.execute('DELETE FROM sent_messages WHERE op_message_id = ?', (op_msg_id,))

        @self.dp.callback_query_handler(lambda query: query.data.startswith('cancel'))
        async def cancel_handler(query: types.CallbackQuery):
            self.cursor.execute('DELETE FROM waiting_pool WHERE user_id = ?', (query.from_user.id,))
            await query.answer('Анкета отменена.')
        
        @self.dp.callback_query_handler(lambda query: query.data == 'blank')
        async def blank_handler(query: types.CallbackQuery): pass

    async def send_waiting_messages(self):
        if not self.rights.waiting_messages: return
        active_operators = [i for i in self.operators['operators'] 
                            if i not in self.rights.offline_operators]
        if not active_operators: return
        for op_id in active_operators:
            for msg in self.rights.waiting_messages:
                sent_message = await self.bot.send_message(
                    op_id,
                    msg['message'].text,
                    reply_markup=msg['reply_markup']
                )
                self.cursor.execute('INSERT INTO sent_messages VALUES (?, ?, ?)', 
                                (op_id, sent_message.message_id, msg['message'].from_user.id))
        self.rights.waiting_messages = []


if __name__ == "__main__":
    bot = HikkiBot('TOKEN', -1000000000000)
    bot.setup_handlers()
    # test exceptions later
    try:
        executor.start_polling(bot.dp, skip_updates=True)
    except BadRequest:
        pass
    except RetryAfter as e:
        sleep(e.timeout)
        executor.start_polling(bot.dp, skip_updates=True)
    except Unauthorized:
        pass
    except TelegramAPIError:
        sleep(.5)
        executor.start_polling(bot.dp, skip_updates=True)