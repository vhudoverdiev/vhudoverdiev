"""Curated questions bound to an exact source video and course section."""
import json
import random
import re
import unicodedata
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load_reviewed_quizzes():
    path = Path(__file__).resolve().parents[1] / 'data' / 'reviewed_quizzes.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def reviewed_questions(lesson):
    if not lesson.course.title.startswith('Python:') or not (lesson.video_url or '').startswith('local:'):
        return None
    filename = Path(lesson.video_url[6:]).name
    clean = re.sub(r'^\s*\[[^]]+\]\s*', '', filename)
    number = re.match(r'\s*(\d+)', clean)
    module = re.match(r'\s*(\d+)', lesson.module_name)
    if not number or not module:
        return None
    entry = load_reviewed_quizzes().get(f'python:{int(number.group(1)):03d}')
    if not entry or entry['module_number'] != int(module.group(1)):
        return None
    if unicodedata.normalize('NFC', entry['source_video']) != unicodedata.normalize('NFC', filename):
        return None
    rng = random.Random(f'reviewed-v1:{lesson.id}')
    questions = []
    for authored in entry['questions']:
        options = list(authored['options'])
        answer = options[authored['correct']]
        rng.shuffle(options)
        questions.append({**authored, 'options': options, 'correct': options.index(answer)})
    return questions
