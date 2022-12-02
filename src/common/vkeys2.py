from interception.stroke import key_stroke
import time
from player_instance import Player
from bind import c, d

p = Player(c, d)

def key_down(key):
    p.key_down(key)

def key_up(key):
    p.key_up(key)

def press(key, n=1, down_time=0.05, up_time=0.1):
    p.press(key, n, down_time, up_time)
    