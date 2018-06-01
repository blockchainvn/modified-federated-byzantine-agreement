import enum

class BaseEnum(enum.Enum):
    @classmethod
    def from_value(cls, value):
        for i in cls:
            if i.value == value:
                return i

        return None

    @classmethod
    def from_name(cls, name):
        return getattr(cls, name)
