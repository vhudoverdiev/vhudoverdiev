"""Fresh, non-blocking congratulations with no repeated scene in a row."""
import secrets
from flask import session


def celebration_for(attempt):
    previous = session.get('last_celebration_scene')
    scenes = ['confetti', 'ribbons', 'stars', 'orbits', 'bubbles', 'diamonds']
    scene = secrets.choice([item for item in scenes if item != previous])
    session['last_celebration_scene'] = scene
    palette = secrets.choice([
        ['#b5e749','#d4ef9c','#8eaf5a','#f4d27e'],
        ['#b9e47d','#d7bbf2','#a4cbdc','#f1d4a0'],
        ['#a8dfbd','#c5e67d','#e9bd9b','#d5c5e7'],
        ['#b5df75','#d7e6ab','#edd58e','#bddfdb'],
    ])
    particles = [{'x': secrets.randbelow(101), 'delay': secrets.randbelow(800),
                  'duration': 2200 + secrets.randbelow(2000), 'size': 5 + secrets.randbelow(9),
                  'rotation': secrets.randbelow(720) - 360, 'color': secrets.choice(palette)} for _ in range(32)]
    return {'scene': scene, 'particles': particles,
            'message': secrets.choice(['Ещё один шаг вперёд. Продолжай в своём ритме.',
                                       'Отличная работа! Знания становятся увереннее.',
                                       'Ты справился. Впереди — новые открытия.',
                                       'Есть результат! Можно двигаться дальше.'])}
