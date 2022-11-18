from aiogram import types
import json

from rights import Rights


def is_admin(self) -> bool:
    return self.id in \
        json.loads(open('rights.json', 'r').read())['admins']

def is_operator(self) -> bool:
    return self.id in \
        json.loads(open('rights.json', 'r').read())['operators']\
        or self.id in \
        json.loads(open('rights.json', 'r').read())['admins']

def op(self):
    Rights().add_operator(self)

def deop(self):
    Rights().remove_operator(self)


types.User.is_admin = is_admin
types.User.is_operator = is_operator
types.User.op = op
types.User.deop = deop

class User(types.User):

    def __init__(self, user_id):
        super().__init__()
        self.id = int(user_id)
