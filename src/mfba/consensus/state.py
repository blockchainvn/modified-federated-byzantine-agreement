import enum
from ..common import (
    BaseEnum,
)

class State(BaseEnum):
    none = enum.auto()
    init = enum.auto()
    sign = enum.auto()
    accept = enum.auto()
    all_confirm = enum.auto()

    @classmethod
    def get_from_value(cls, v):
        for i in list(cls):
            if i.value == v:
                return i

        return

    def get_next(self):
        for i in list(self.__class__):
            if i.value > self.value:
                return i

        return None

    def is_next(self, state):
        return state.value > self.value

    def __gt__(self, state):
        return self.value > state.value

    def __lt__(self, state):
        return self.value < state.value

    def __ge__(self, state):
        return self.value >= state.value

    def __le__(self, state):
        return self.value <= state.value

    def __eq__(self, state):
        return self.value == state.value