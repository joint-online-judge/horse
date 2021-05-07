from enum import Enum, auto


class Color(Enum):
    TEST = 10
    RED = auto()
    BLUE = auto()
    GREEN = auto()


res = list(Color)
print(res)
