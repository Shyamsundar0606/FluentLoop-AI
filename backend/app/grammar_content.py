"""Validate and add the A1 grammar supplements to an isolated curriculum."""
import hashlib
import json
import unicodedata
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from sqlalchemy import select

from app.content_import import _provenance, _upsert
from app.curriculum_models import (
    ContentProvenance, ContentSource, Course, Exercise, ExerciseOption, GrammarExample,
    GrammarRule, GrammarTopic, ImportBatch, LearningObjective, Lesson, LessonGrammar,
    LessonObjective, LessonSection, LessonVocabulary, Lexeme, Unit, VerbConjugation, VerbLemma,
)
from app.interactive_content import ExerciseInput, Mistake, Strict
from app.services.exercise_formats import definition
from app.services.grading_service import normalize_written

CONTENT_PATH = Path(__file__).resolve().parents[1] / "content/practice/a1-grammar-0.1.0.json"
COURSE = "m083-a1-grammar"
EXISTING_TOPIC = "subject-pronouns-etre"
REVIEW_AREAS = ("linguistic_accuracy", "phonetics", "pedagogy", "answer_keys", "licensing")
VERBS = {EXISTING_TOPIC: "être", "avoir-present": "avoir", "common-present-verbs": "parler"}
SUBJECTS = ("je", "tu", "il / elle", "nous", "vous", "ils / elles")


class Topic(Strict):
    slug: str = Field(pattern=r"^[a-z][a-z0-9-]{2,90}$")
    source_lesson: str = Field(pattern=r"^a1-0(0[1-9]|10)$")
    objective: str = Field(min_length=5)
    situation: str = Field(min_length=3, max_length=80)
    title: str = Field(min_length=5, max_length=160)
    explanation: str = Field(min_length=30, max_length=2000)
    when_to_use: str = Field(min_length=15, max_length=1000)
    recap: str = Field(min_length=15, max_length=1000)
    vocabulary: list[str] = Field(min_length=1, max_length=8)
    examples: list[tuple[str, str]] = Field(min_length=3, max_length=5)
    vocabulary_examples: dict[str, int]
    noun_forms: dict[str, tuple[str, str]] = Field(default_factory=dict)
    common_mistakes: list[Mistake] = Field(min_length=1, max_length=5)
    forms: list[tuple[str, str]] = Field(default_factory=list, max_length=6)
    exercises: list[ExerciseInput] = Field(max_length=6)

    @model_validator(mode="after")
    def validate_links_and_keys(self):
        if len(set(self.vocabulary)) != len(self.vocabulary):
            raise ValueError("Vocabulary references must be unique")
        examples = dict(self.examples)
        if len(examples) != len(self.examples) or any(not fr.strip() or not en.strip() for fr, en in self.examples):
            raise ValueError("Examples need distinct French sentences and English translations")
        if set(self.vocabulary_examples) != set(self.vocabulary) or any(
            not 1 <= index <= len(self.examples) for index in self.vocabulary_examples.values()
        ):
            raise ValueError("Link each vocabulary item to an example in this topic")
        if not self.noun_forms.keys() <= set(self.vocabulary) or any(
            not singular or not plural or singular == plural for singular, plural in self.noun_forms.values()
        ):
            raise ValueError("Provide distinct singular and plural forms for linked nouns")
        keys = {exercise.key for exercise in self.exercises}
        if len(keys) != len(self.exercises) or (self.slug != EXISTING_TOPIC and len(keys) < 2):
            raise ValueError("Each new topic lesson needs at least two distinct exercises")
        if self.slug == EXISTING_TOPIC and keys:
            raise ValueError("The existing être fixture owns its exercise keys")
        if self.slug in VERBS:
            subjects = ("j’", *SUBJECTS[1:]) if self.slug == "avoir-present" else SUBJECTS
            if tuple(subject for subject, _ in self.forms) != subjects or any(not form for _, form in self.forms):
                raise ValueError("Use the six ordered present-tense subject rows")
        elif self.forms:
            raise ValueError("This topic does not have a present-tense table")
        for exercise in self.exercises:
            data = exercise.data
            choices = [normalize_written(option) for option in exercise.options]
            if "" in choices or len(set(choices)) != len(choices):
                raise ValueError("Choice options must be nonempty and distinct")
            if exercise.type == "listening" and examples.get(data["text_fr"]) != exercise.options[exercise.correct_option]:
                raise ValueError("Listening audio and its answer must match a bilingual teaching example")
            if exercise.type in ("fill_blank", "short_answer"):
                answers = [normalize_written(answer) for answer in data["accepted_answers"]]
                if "" in answers or len(set(answers)) != len(answers):
                    raise ValueError("Written answer variants must be nonempty and distinct after normalization")
            if exercise.type == "sentence_order":
                words = {item["id"]: item["text"] for item in data["tiles"]}
                for order in data["accepted_orders"]:
                    sentence = " ".join(words[tile] for tile in order)
                    if normalize_written(sentence) != normalize_written(data["correct_sentence"]):
                        raise ValueError("The sentence-order key must reconstruct the feedback sentence")
        return self


class Supplement(Strict):
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    level: Literal["A1"]
    status: Literal["draft"]
    source_license: str = Field(min_length=15, max_length=160)
    attribution: str = Field(min_length=15, max_length=1000)
    topics: list[Topic] = Field(min_length=13, max_length=13)

    @model_validator(mode="after")
    def validate_topics(self):
        if len({topic.slug for topic in self.topics}) != len(self.topics):
            raise ValueError("Duplicate grammar topic")
        if [topic.source_lesson for topic in self.topics] != sorted(topic.source_lesson for topic in self.topics):
            raise ValueError("Teach topics in the existing A1 lesson order")
        return self


def load_supplement(path=CONTENT_PATH):
    raw = path.read_text(encoding="utf-8")
    if unicodedata.normalize("NFC", raw) != raw or "\ufffd" in raw:
        raise ValueError("Use NFC French text without replacement characters")
    return Supplement.model_validate_json(raw)


def _resolve(db, item, level):
    linked = db.execute(
        select(Lesson, GrammarTopic, LearningObjective)
        .join(LessonGrammar, LessonGrammar.lesson_id == Lesson.id)
        .join(GrammarTopic, GrammarTopic.id == LessonGrammar.grammar_topic_id)
        .join(LessonObjective, LessonObjective.lesson_id == Lesson.id)
        .join(LearningObjective, LearningObjective.id == LessonObjective.objective_id)
        .where(Lesson.slug == item.source_lesson, GrammarTopic.slug == item.slug,
               LearningObjective.code == item.objective, Lesson.difficulty_level == level,
               GrammarTopic.cefr_level == level, LearningObjective.level == level)
    ).one_or_none()
    if linked is None:
        raise ValueError(f"Missing matching A1 lesson, topic or objective for {item.slug}")
    source_lesson, topic, objective = linked
    published = db.scalar(
        select(Lesson.id).join(LessonGrammar).join(Unit, Unit.id == Lesson.unit_id).join(Course)
        .where(LessonGrammar.grammar_topic_id == topic.id, Lesson.status == "published",
               Unit.status == "published", Course.status == "published")
    )
    reviewed = db.scalar(
        select(ContentProvenance.id).where(ContentProvenance.item_type == "grammar_topic",
            ContentProvenance.item_key == item.slug,
            ContentProvenance.review_state.in_(("human_reviewed", "published"))).limit(1)
    )
    if topic.publication_status not in ("inherited", "draft") or published or reviewed:
        raise ValueError(f"Refusing to replace protected grammar topic {item.slug}")
    words = {lemma: (part_of_speech, link) for lemma, part_of_speech, link in db.execute(
        select(Lexeme.lemma, Lexeme.part_of_speech, LessonVocabulary)
        .join(LessonVocabulary, LessonVocabulary.lexeme_id == Lexeme.id)
        .where(LessonVocabulary.lesson_id == source_lesson.id)
    )}
    if not set(item.vocabulary) <= words.keys():
        raise ValueError(f"Unknown vocabulary in {item.slug}: {set(item.vocabulary) - words.keys()}")
    if any(words[word][0] != "noun" for word in item.noun_forms):
        raise ValueError(f"Noun forms must refer to nouns in {item.slug}")
    if item.forms:
        forms = db.scalars(select(VerbConjugation.conjugated_form).join(VerbLemma)
            .where(VerbLemma.infinitive == VERBS[item.slug], VerbConjugation.mood == "indicative",
                   VerbConjugation.tense == "present")
            .order_by(VerbConjugation.grammatical_number.desc(), VerbConjugation.grammatical_person)).all()
        if list(forms) != [form for _, form in item.forms]:
            raise ValueError(f"Present forms disagree with the existing verb reference for {item.slug}")
    return topic, objective, [words[word][1] for word in item.vocabulary]


def import_supplement(db, pack):
    """Install once. A revised answer set needs a new release and exercise identities."""
    digest = hashlib.sha256(pack.model_dump_json().encode("utf-8")).hexdigest()
    batch = db.scalar(select(ImportBatch).where(ImportBatch.batch_key == f"{COURSE}-{pack.version}"))
    if batch is not None:
        if batch.report.get("sha256") != digest:
            raise ValueError("An installed release is immutable")
        return {**batch.report, "unchanged": True}
    if db.scalar(select(Course.id).where(Course.slug == COURSE)):
        raise ValueError("A new release needs a new course and exercise identities")

    items = [_resolve(db, item, pack.level) for item in pack.topics]
    source = ContentSource(source_name="FluentLoop A1 grammar supplements", source_type="ai_assisted_draft",
                           source_license=pack.source_license, attribution_requirements=pack.attribution)
    db.add(source)
    db.flush()
    batch = ImportBatch(source_id=source.id, batch_key=f"{COURSE}-{pack.version}",
                        content_version=pack.version, status="running", report={})
    db.add(batch)
    db.flush()
    course = _upsert(db, Course, {"slug": COURSE}, dict(
        level_id=pack.level, title="A1 grammar and everyday French", description="Short draft lessons with examples and linked practice.",
        explanation_language="en", estimated_minutes=6 * sum(bool(item.exercises) for item in pack.topics),
        status=pack.status, content_version=pack.version))
    unit = _upsert(db, Unit, {"course_id": course.id, "slug": "guided-grammar"}, dict(
        title="Grammar in everyday situations", description=course.description, sequence_order=1, status=pack.status))
    _provenance(db, source, batch, "course", COURSE, pack.version)

    for order, (item, (topic, objective, vocabulary)) in enumerate(zip(pack.topics, items), 1):
        key = f"m083-{item.slug}"
        lesson_slug = key if item.exercises else "m08-etre-interactive-lesson"
        topic.publication_status = "draft"
        topic.teaching_metadata = dict(
            rule_code=key, curriculum_supplement=True, preferred_lesson_slug=lesson_slug,
            objective_code=item.objective, situation=item.situation, version=pack.version, sequence=order,
            vocabulary_examples={word: item.examples[index - 1] for word, index in item.vocabulary_examples.items()},
            noun_forms=item.noun_forms,
            when_to_use=item.when_to_use, recap=item.recap, forms=item.forms,
            common_mistakes=[mistake.model_dump() for mistake in item.common_mistakes],
            source_license=pack.source_license, attribution=pack.attribution,
            independent_human_review=False)
        rule = _upsert(db, GrammarRule, {"topic_id": topic.id, "rule_code": key}, dict(
            explanation_english=item.explanation, explanation_french=None, exceptions=None))
        for french, english in item.examples:
            _upsert(db, GrammarExample, {"rule_id": rule.id, "french_sentence": french,
                    "english_translation": english}, {"explanation": None})
        _provenance(db, source, batch, "grammar_topic", item.slug, pack.version)
        _provenance(db, source, batch, "grammar_rule", key, pack.version)
        if item.exercises:
            _add_lesson(db, pack, item, order, unit, topic, objective, vocabulary, source, batch, key)

    batch.status = "completed"
    batch.report = dict(sha256=digest, topics=len(pack.topics), lessons=sum(bool(t.exercises) for t in pack.topics),
                        exercises=sum(len(t.exercises) for t in pack.topics), status="draft",
                        review={area: "pending" for area in REVIEW_AREAS})
    db.flush()
    return batch.report


def _add_lesson(db, pack, item, order, unit, topic, objective, vocabulary, source, batch, key):
    lesson = _upsert(db, Lesson, {"unit_id": unit.id, "slug": key}, dict(
        title=item.title, description=item.when_to_use, sequence_order=order, estimated_minutes=6,
        difficulty_level=pack.level, explanation_language="en", status="draft", content_version=pack.version))
    _upsert(db, LessonObjective, {"lesson_id": lesson.id, "objective_id": objective.id}, {})
    _upsert(db, LessonGrammar, {"lesson_id": lesson.id, "grammar_topic_id": topic.id}, {})
    for position, word in enumerate(vocabulary, 1):
        _upsert(db, LessonVocabulary, {"lesson_id": lesson.id, "lexeme_id": word.lexeme_id},
                {"sequence_order": position, "teaching_note": word.teaching_note})
    examples = "\n".join(f"{fr}\n{en}" for fr, en in item.examples)
    explanation = "\n".join([item.explanation, *(f"{subject} {form}" for subject, form in item.forms)])
    for position, (kind, title, body) in enumerate((
        ("introduction", "Understand", item.when_to_use),
        ("grammar", "Explanation", explanation),
        ("explanation", "French examples", examples),
        ("recap", "Remember", item.recap),
    ), 1):
        _upsert(db, LessonSection, {"lesson_id": lesson.id, "sequence_order": position},
                dict(section_type=kind, title=title, body_content=body, content_metadata={}))
    for position, entry in enumerate(item.exercises, 1):
        exercise = _upsert(db, Exercise, {"lesson_id": lesson.id, "sequence_order": position}, dict(
            exercise_type=entry.type, prompt=entry.prompt, instructions=entry.instructions, explanation=entry.explanation,
            level=pack.level, exercise_data=definition(entry.type, entry.data), grammar_topic_id=topic.id,
            learning_objective_id=objective.id))
        for number, option in enumerate(entry.options, 1):
            _upsert(db, ExerciseOption, {"exercise_id": exercise.id, "sequence_order": number},
                    dict(option_text=option, is_correct=number - 1 == entry.correct_option))
        _provenance(db, source, batch, "exercise", f"{key}:{entry.key}", pack.version)
    _provenance(db, source, batch, "lesson", key, pack.version)


if __name__ == "__main__":
    pack = load_supplement()
    print(json.dumps(dict(version=pack.version, topics=len(pack.topics), status=pack.status)))
