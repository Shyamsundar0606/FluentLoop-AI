"""Bounded, published learning evidence for the existing tutor."""
import re
import unicodedata

from sqlalchemy import func, select

from app.ai.models import Conversation, Message
from app.api.v1.curriculum import _published_lesson_filter
from app.curriculum_models import Course, GrammarTopic, Lesson, LessonGrammar, LessonVocabulary, Lexeme, Unit, WordSense
from app.learning_models import ExerciseAttempt, LearningSession, LessonProgress
from app.models import utcnow
from app.services.learning_service import lesson_vocabulary
from app.study_models import ReviewCard

EXAMPLES = {
    "je m'appelle": ("my name is", "Je m’appelle Camille."),
    "une baguette": ("a baguette", "Je voudrais une baguette, s’il vous plaît."),
    "menu": ("menu", "Puis-je voir le menu ?"),
    "rayon": ("aisle or department", "Dans quel rayon se trouve le riz ?"),
    "à gauche": ("on the left", "La gare est à gauche."),
    "un billet": ("a ticket", "Je voudrais un billet pour Lyon."),
    "les horaires": ("opening hours", "Quels sont les horaires de la pharmacie ?"),
    "depuis": ("since or for", "Dans cette scène, j’ai mal depuis hier."),
    "rendez-vous": ("appointment", "Je voudrais prendre rendez-vous."),
    "compétences": ("skills", "Je voudrais développer mes compétences."),
}


def scenario_words(scenario):
    return [dict(french=word, english=EXAMPLES[word][0], example=EXAMPLES[word][1])
            for word in scenario.suggested_vocabulary if word in EXAMPLES] if scenario else []


def evidence(db, user, level, conversation_id):
    visible = select(Lesson.id).join(Unit).join(Course).where(
        _published_lesson_filter(False), Course.level_id == level)
    completed = db.execute(select(LessonProgress.lesson_id).where(
        LessonProgress.user_id == user.id, LessonProgress.lesson_id.in_(visible),
        LessonProgress.status == "completed").order_by(LessonProgress.last_studied_at.desc()).limit(5)).scalars().all()
    topics = db.scalars(select(GrammarTopic.title).join(LessonGrammar).where(
        LessonGrammar.lesson_id.in_(completed), GrammarTopic.publication_status.in_(("inherited", "published"))
    ).distinct().order_by(GrammarTopic.title).limit(4)).all()
    mistakes = db.scalars(select(ExerciseAttempt.id).join(LearningSession,
        LearningSession.id == ExerciseAttempt.learning_session_id).join(Lesson, Lesson.id == LearningSession.lesson_id)
        .where(ExerciseAttempt.user_id == user.id, LearningSession.user_id == user.id,
               Lesson.id.in_(visible), LearningSession.lesson_content_version == Lesson.content_version,
               ExerciseAttempt.is_correct.is_(False))
        .order_by(ExerciseAttempt.submitted_at.desc()).limit(8)).all()
    cards = db.execute(select(Lexeme.lemma, WordSense.explanation_english, ReviewCard.recent_result)
        .select_from(ReviewCard).join(WordSense, WordSense.id == ReviewCard.word_sense_id)
        .join(Lexeme, Lexeme.id == WordSense.lexeme_id).where(
            ReviewCard.user_id == user.id, ReviewCard.cefr_level == level, ReviewCard.next_due_at <= utcnow(),
            Lexeme.id.in_(select(LessonVocabulary.lexeme_id).where(LessonVocabulary.lesson_id.in_(visible)))
        ).order_by(ReviewCard.next_due_at, ReviewCard.id).limit(5)).all()
    previous = db.scalar(select(func.count()).select_from(Conversation).where(
        Conversation.user_id == user.id, Conversation.id != conversation_id, Conversation.cefr_level == level,
        Conversation.preview_mode.is_(False), Conversation.last_message_at.is_not(None)))
    studied = lesson_vocabulary(db, completed) if completed else {}
    words = {}
    for lesson_words in studied.values():
        for word in lesson_words:
            words.setdefault(word["lemma"], word["translation"])
    return dict(completed_lessons=len(completed), studied_grammar=topics, recent_incorrect_attempts=len(mistakes),
                prior_conversations_with_messages=previous, goal_minutes=user.preferences.daily_study_minutes,
                learning_focus=user.preferences.learning_focus,
                studied_vocabulary=[dict(french=word, english=meaning[:160]) for word, meaning in list(words.items())[:5]],
                due_vocabulary=[dict(french=word, english=meaning[:160], recently_missed=correct is False)
                                for word, meaning, correct in cards])


def summary(db, conversation, scenario):
    messages = db.scalars(select(Message).where(
        Message.conversation_id == conversation.id, Message.response_status == "success"
    ).order_by(Message.created_at, Message.id)).all()
    corrections = [message.model_metadata["correction"] for message in messages
                   if message.role == "assistant" and message.model_metadata.get("correction")]
    learner_messages = [message.content for message in messages if message.role == "user"]
    def normalize(value):
        return unicodedata.normalize("NFC", value).casefold().replace("’", "'")
    used = [word for word in scenario.suggested_vocabulary
            if any(re.search(r"(?<!\w)" + re.escape(normalize(word)) + r"(?!\w)", normalize(text))
                   for text in learner_messages)] if scenario else []
    return dict(messages_exchanged=len(messages), learner_turns=len(learner_messages),
                corrections=corrections[-30:], correction_count=len(corrections), used_vocabulary=used,
                scenario_goals=scenario.completion_criteria if scenario else [],
                target_turns=scenario.target_turns if scenario else None)
