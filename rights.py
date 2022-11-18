from aiogram import types
import json


class Rights:

    def __init__(self):
        with open('rights.json', 'r') as f:
            self.operators: dict = json.loads(f.read())
        self.offline_operators = set()
        self.waiting_messages = []

    def add_operator(self, user: types.User):
        if user.id not in self.operators['operators']:
            self.operators['operators'].append(user.id)
            with open('rights.json', 'w') as f:
                json.dump(self.operators, f, indent=4)

    def add_admin(self, user: types.User):
        if user.id not in self.operators['admins']:
            self.operators['admins'].append(user.id)
            with open('rights.json', 'w') as f:
                json.dump(self.operators, f, indent=4)

    def remove_operator(self, user: types.User):
        if user.id in self.operators['operators']:
            self.operators['operators'].remove(user.id)
            with open('rights.json', 'w') as f:
                json.dump(self.operators, f, indent=4)

        if user.id in self.operators['admins']:
            self.operators['admins'].remove(user.id)
            with open('rights.json', 'w') as f:
                json.dump(self.operators, f, indent=4)

    def get_active_operators(self):
        return [i for i in self.operators['operators'] 
                if i not in self.offline_operators]

    def operator_checker(self, message: types.Message):
        return message.from_user.is_operator()

    def admin_checker(self, message: types.Message):
        return message.from_user.is_admin()
