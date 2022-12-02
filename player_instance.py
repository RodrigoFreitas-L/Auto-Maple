from interception.stroke import key_stroke
import time
from random import random

SC_DECIMAL_ARROW = {
    "left": 75, "right": 77, "down": 80, "up": 72,
}

SC_DECIMAL = {
    'esc': 1,
    '1': 2,
    '2': 3,
    '3': 4,
    '4': 5,
    '5': 6,
    '6': 7,
    '7': 8,
    '8': 9,
    '9': 10,
    '0': 11,
    '-': 12,
    '=': 13,
    'tab': 15,
    'q': 16,
    'w': 17,
    'e': 18,
    'r': 19,
    't': 20,
    'y': 21,
    'u': 22,
    'i': 23,
    'o': 24,
    'p': 25,
    'enter': 28,
    'ctrol': 29,
    'a': 30,
    's': 31,
    'd': 32,
    'f': 33,
    'g': 34,
    'h': 35,
    'j': 36,
    'k': 37,
    'l': 38,
    'shift': 42,
    'z': 44,
    'x': 45,
    'c': 46,
    'v': 47,
    'b': 48,
    'n': 49,
    'm': 50,
    'alt': 56,
    'space': 57,
    'capslock': 58,
    'f1': 59,
    'f2': 60,
    'f3': 61,
    'f4': 62,
    'f5': 63,
    'f6': 64,
    'f7': 65,
    'f8': 66,
    'f9': 67,
    'f10': 68,
    'end': 79,
    'page down': 81,
    'ins': 82,
    'del': 83,
    'page up': 73,
    'home': 71
}

# Change these to your own settings.
JUMP_KEY = "SPACE"
ROPE_LIFT_KEY = "D"

class Player:


    def __init__(self, context, device):
        # interception
        self.context = context
        self.device = device
        
    def key_down(self, key):
        
        if key in SC_DECIMAL_ARROW:
            self.context.send(self.device, key_stroke(SC_DECIMAL_ARROW[key], 2, 0))
        else:
            self.context.send(self.device, key_stroke(SC_DECIMAL[key], 0, 0))

    def key_up(self, key):

        if key in SC_DECIMAL_ARROW:
            self.context.send(self.device, key_stroke(SC_DECIMAL_ARROW[key], 3, 0))
        else:
            self.context.send(self.device, key_stroke(SC_DECIMAL[key], 1, 0))

    def press(self, key, n, down_time, up_time):
        for _ in range(n):
            self.key_down(key)
            time.sleep(down_time * (0.8 + 0.4 * random()))
            self.key_up(key)
            time.sleep(up_time * (0.8 + 0.4 * random()))
                 