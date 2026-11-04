"""Original roleplay prompts v1, authored for this feature; not reviewed courses.

These are independent practice situations, with no imported curriculum dependency.
Publication here makes the scenario prompt available, not model answers verified.
"""

from pydantic import BaseModel
from app.ai.response_schemas import Level


class Scenario(BaseModel):
    id: str
    title: str
    cefr_level: Level
    description: str
    tutor_role: str
    learner_role: str
    opening_situation: str
    learning_objectives: list[str]
    suggested_vocabulary: list[str]
    target_grammar: list[str]
    conversation_constraints: list[str]
    evaluation_guidance: str
    provenance: str = (
        "Original FluentLoop practice prompt v1; not expert-reviewed curriculum"
    )
    publication_status: str = "published_practice_prompt"


DEFINITIONS = {
    "A1": [
        (
            "greeting-neighbor",
            "Greeting a neighbor",
            "neighbor",
            "neighbor",
            "Say hello outside your home.",
            ["bonjour", "ça va"],
            ["greetings"],
        ),
        (
            "introductions",
            "Introducing yourself",
            "new acquaintance",
            "new acquaintance",
            "Meet someone for the first time.",
            ["je m'appelle", "enchanté"],
            ["être", "s'appeler"],
        ),
        (
            "boulangerie",
            "Ordering at a boulangerie",
            "shop assistant",
            "customer",
            "Enter a boulangerie to buy bread.",
            ["une baguette", "s'il vous plaît"],
            ["articles", "je voudrais"],
        ),
        (
            "price",
            "Asking for a price",
            "seller",
            "customer",
            "Ask how much an item costs.",
            ["combien", "euros"],
            ["questions"],
        ),
    ],
    "A2": [
        (
            "supermarket",
            "Shopping at a supermarket",
            "employee",
            "shopper",
            "Find ingredients for dinner.",
            ["rayon", "acheter"],
            ["quantities"],
        ),
        (
            "appointment",
            "Making an appointment",
            "receptionist",
            "visitor",
            "Arrange an appointment.",
            ["rendez-vous", "disponible"],
            ["future expressions"],
        ),
        (
            "directions",
            "Asking for directions",
            "local resident",
            "traveler",
            "Find your way to the station.",
            ["à gauche", "tout droit"],
            ["imperative"],
        ),
        (
            "restaurant",
            "Ordering at a restaurant",
            "server",
            "guest",
            "Order a meal and ask about the menu.",
            ["menu", "addition"],
            ["polite requests"],
        ),
    ],
    "B1": [
        (
            "experience",
            "Describing a past experience",
            "interested friend",
            "storyteller",
            "Tell a friend about a memorable day.",
            ["ensuite", "souvenir"],
            ["passé composé", "imparfait"],
        ),
        (
            "work-studies",
            "Talking about work or studies",
            "acquaintance",
            "student or worker",
            "Discuss your daily responsibilities.",
            ["études", "métier"],
            ["relative clauses"],
        ),
        (
            "travel",
            "Discussing travel plans",
            "travel companion",
            "traveler",
            "Plan a trip together.",
            ["séjour", "prévoir"],
            ["future"],
        ),
    ],
    "B2": [
        (
            "interview",
            "Job interview practice",
            "interviewer",
            "candidate",
            "Discuss a fictional job application.",
            ["compétences", "expérience"],
            ["conditional"],
        ),
        (
            "workplace",
            "Discussing a workplace issue",
            "colleague",
            "colleague",
            "Resolve a scheduling disagreement.",
            ["compromis", "échéance"],
            ["subjunctive"],
        ),
        (
            "opinions",
            "Expressing arguments and opinions",
            "discussion partner",
            "participant",
            "Discuss the benefits of remote work.",
            ["néanmoins", "en revanche"],
            ["concession"],
        ),
    ],
    "C1": [
        (
            "formal",
            "Formal professional conversation",
            "professional contact",
            "project lead",
            "Negotiate a fictional project proposal.",
            ["enjeux", "modalités"],
            ["formal register"],
        ),
        (
            "social-topic",
            "Discussing a complex social topic",
            "moderator",
            "participant",
            "Discuss urban transport policy.",
            ["mobilité", "équité"],
            ["nuanced argument"],
        ),
        (
            "argument",
            "Presenting an argument",
            "audience member",
            "presenter",
            "Defend a proposal for a public library.",
            ["dès lors", "certes"],
            ["rhetorical structure"],
        ),
    ],
    "C2": [
        (
            "debate",
            "Nuanced debate",
            "debate partner",
            "debater",
            "Explore the tension between tradition and innovation.",
            ["à cet égard", "nuancer"],
            ["concession", "implicit meaning"],
        ),
        (
            "professional",
            "Sophisticated professional dialogue",
            "negotiator",
            "negotiator",
            "Resolve competing priorities in a fictional organization.",
            ["arbitrage", "consensus"],
            ["register shifts"],
        ),
        (
            "style",
            "Advanced linguistic style practice",
            "editor",
            "author",
            "Discuss alternative formulations of a short French text.",
            ["connotation", "tournure"],
            ["style", "subtle meaning"],
        ),
    ],
}
SCENARIOS = [
    Scenario(
        id=level.lower() + "-" + key,
        title=title,
        cefr_level=level,
        description=opening,
        tutor_role=tutor,
        learner_role=learner,
        opening_situation=opening,
        learning_objectives=[
            "Sustain a conversation about: " + title,
            "Ask and answer relevant questions",
        ],
        suggested_vocabulary=vocab,
        target_grammar=grammar,
        conversation_constraints=[
            "Use fictional details; do not request sensitive personal information",
            "Offer hints on request",
            "Keep each turn appropriate to the learner level",
        ],
        evaluation_guidance="On finish, summarize observed strengths and specific mistakes only; no formal proficiency assessment.",
    )
    for level, rows in DEFINITIONS.items()
    for key, title, tutor, learner, opening, vocab, grammar in rows
]


def scenario_by_id(key):
    return next((s for s in SCENARIOS if s.id == key), None)
