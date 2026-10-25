"""Stable, lesson-scoped checks; interview libraries never receive quizzes."""
import random
import re

from ..models import Lesson
from .quiz_bank import facts_for


def questions_for_lesson(lesson):
    if lesson.course.course_type == "library":
        return []
    if lesson.course.title.startswith('Английский') and not lesson.quiz_data:
        from pathlib import Path
        from .english_lesson_bank import LESSONS
        filename = Path((lesson.video_url or '').removeprefix('local:')).name or lesson.title
        filename = re.sub(r'^\[[^]]+\]\s*', '', filename)
        number = re.match(r'\s*(\d+)', filename)
        rows = LESSONS.get(int(number.group(1))) if number else None
        if rows:
            facts = [row.split('|', 1) for row in rows.splitlines()]
            rng = random.Random(f'english-lesson-v1:{lesson.id}')
            questions = []
            for term, definition in facts:
                options = [definition] + rng.sample([text for other, text in facts if other != term], 3)
                rng.shuffle(options)
                questions.append({'prompt': f'Какое описание соответствует понятию «{term}»?',
                                  'options': options, 'correct': options.index(definition),
                                  'explanation': f'{term} — {definition[0].lower() + definition[1:]}.'})
            return questions
    topic_check = lesson if lesson.quiz_data else Lesson.query.filter_by(
        course_id=lesson.course_id, module_name=lesson.module_name
    ).filter(Lesson.quiz_data.isnot(None)).order_by(Lesson.position).first()
    authored = list(topic_check.quiz_data or []) if topic_check else []
    title = lesson.course.title
    kind = 'ai' if title.startswith('AI Developer') else 'english' if title.startswith('Английский') else 'python' if title.startswith('Python:') else None
    match = re.match(r'\s*(\d+)', lesson.module_name)
    facts = facts_for(kind, int(match.group(1))) if kind and match else []
    if not facts:
        return authored
    rng = random.Random(f'lesson-check-v1:{lesson.id}:{lesson.module_name}')
    questions = authored[:3]
    # Include topic terminology first, followed by core concepts for spaced review.
    topic_facts, core_facts = facts[:10], facts[10:]
    rng.shuffle(core_facts)
    authored_prompts = ' '.join(q['prompt'] for q in questions)
    selected = [(term, definition) for term, definition in topic_facts + core_facts
                if not re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', authored_prompts, re.IGNORECASE)]
    for term, definition in selected[:20 - len(questions)]:
        alternatives = [other for _, other in facts if other != definition]
        options = [definition] + rng.sample(alternatives, min(3, len(alternatives)))
        rng.shuffle(options)
        questions.append({
            'prompt': f'Какое описание соответствует понятию «{term}»?',
            'options': options,
            'correct': options.index(definition),
            'explanation': f'{term} — {definition[0].lower() + definition[1:]}.',
        })
    # Different deterministic subsets per lesson; no option changes during an attempt.
    return rng.sample(questions, min(10, len(questions)))
