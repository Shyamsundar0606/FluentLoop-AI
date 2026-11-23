"""Build authored draft manuscripts only. No database writes are performed."""
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

VERSION = "0.2.1"

GAP_INSTRUCTIONS = {
    "A1": ["Complete the full ne…pas negation with its missing negative word.",
           "Complete the fixed question pattern est-ce que.",
           "Use the memorised polite request je voudrais + infinitive."],
    "A2": ["Use aller in the present, nous form, to form the near future.",
           "Write the past participle of prendre in the passé composé.",
           "Choose qui or que: the relative pronoun is the subject of vend."],
    "B1": ["Use travailler in the imparfait, je form.",
           "Use pouvoir in the conditional present, vous form; keep the existing hyphen.",
           "Use prendre in the present subjunctive, je form."],
    "B2": ["Use être in the present subjunctive, third-person singular.",
           "Write the past participle of souhaiter after j’aurais.",
           "Use the relative pronoun replacing de in avoir besoin de."],
    "C1": ["Use avoir in the conditional present, nous form, as the conditional-past auxiliary.",
           "Use être in the conditional present, third-person singular, for a future viewed from the past.",
           "Use être in the present subjunctive, third-person singular."],
    "C2": ["Use être in the present subjunctive, third-person singular.",
           "Use être in the present subjunctive, third-person plural, agreeing with ces réserves.",
           "Use convenir in the present subjunctive, third-person singular."],
}

# Near-meaning listening distractors, reviewed separately from the French keys.
LISTENING_DISTRACTORS = {
    "A1": [("I take sugar.", "I do not take milk."),
           ("Does the bus go to the town hall?", "Does the train go to the station?"),
           ("I would like to cancel an appointment.", "I would like to change an appointment.")],
    "A2": [("We visited the flat yesterday.", "We are going to visit the flat today."),
           ("Yesterday, I missed the train.", "Tomorrow, I will take the train."),
           ("It is a ticket office that checks tickets.", "It is a ticket office that exchanges tickets.")],
    "B1": [("When I was a student, I used to work in the mornings.", "When I was a student, I used to study in the evenings."),
           ("Could you change the working hours?", "Could you confirm the address?"),
           ("I need to cancel an appointment.", "I need to attend the meeting.")],
    "B2": [("Because the journey is long, I prefer the train.", "Although the journey is short, I prefer the train."),
           ("I would have liked to receive an answer later.", "I would have liked to send an answer earlier."),
           ("Here is the document I need.", "Here is the document you have already sent.")],
    "C1": [("If this measure had been evaluated, we would have encountered this pitfall.", "If this measure were evaluated now, we could avoid this pitfall."),
           ("The manager indicated that the file had already been examined.", "The manager indicated that the file would be closed."),
           ("It would seem that this conclusion is definitive.", "It would seem that this conclusion is delayed.")],
    "C2": [("But that promise has already been followed by action.", "But that promise no longer needs to be followed by action."),
           ("However well-founded these reservations may be, they settle the entire debate.", "However poorly founded these reservations may be, they settle the entire debate."),
           ("Even assuming that this wording is suitable, its scope is already clear.", "Even assuming that this wording is unsuitable, its scope need not be clarified.")],
}

WRITING_TASKS = {
    "A1": ["Write a short shopping list and two simple sentences about what you want and do not want.",
           "Write a short question asking how to get to the station, then give two simple directions.",
           "Write a short appointment request. Give your invented name and a day and time when you are available."],
    "A2": ["Write a short message arranging a flat viewing. Ask about the floor, charges and journey time.",
           "Write a short account of a delayed journey. Say what happened first, next and finally.",
           "Write a simple ticket request. Specify a day, outward and return times, and whether you want a direct train."],
    "B1": ["Describe an earlier routine and one event that changed it. Distinguish repeated habits from the specific event.",
           "Write an interview follow-up explaining your interest and asking politely for clarification of the hours and priority tasks.",
           "Write to arrange a study appointment. Explain its purpose, ask what to prepare, and say what you would do if unavailable."],
    "B2": ["Write a reasoned contribution to the transport discussion. Defend one option, acknowledge a constraint and propose a qualified compromise.",
           "Write two versions of a follow-up: a direct neutral request and a more formal version. Explain briefly how the tone changes.",
           "Write a clear formal reply enclosing the requested fictional document, identifying the file and asking about the next step. Then summarise it informally for a friend."],
    "C1": ["Write a structured evaluation of the university proposal. Separate evidence from counterfactual inference, address an objection and propose explicit trial criteria.",
           "Write a meeting report distinguishing agreed decisions, reported future actions and unresolved points. Preserve uncertainty and identify what requires confirmation.",
           "Write a synthesis comparing the two viewpoints in the passage. Explain their different time scales, identify a convergence and qualify your own conclusion without inventing evidence."],
    "C2": ["Write an incisive commentary on the promise. Analyse its implied remaining condition, distinguish rhetorical effect from evidence and reformulate the criticism for a non-specialist audience.",
           "Write a nuanced response to the committee's reservations. Concede their force, delimit what they establish and explain what remains unresolved. Finish with an accessible paraphrase that preserves the nuance.",
           "Write two versions of the disagreement: an informal spoken exchange and a formal report. Explain how commitment, irony and presuppositions change with the audience."],
}


def exercises(level, number, skill, row):
    _, _, _, _, explanation, model, translation, gap, expected, words, question, choices = row
    def uid(key):
        return str(uuid5(NAMESPACE_URL, f"fluentloop:personal:{VERSION}:{level}:{number}:{skill}:{key}"))
    def item(key, kind, prompt, instructions, data=None, options=None):
        result = dict(key=key, type=kind, prompt=prompt, instructions=instructions,
                      explanation=explanation, data=data or {})
        if options:
            # Stable variation prevents learning the answer position instead of French.
            correct = (number + ("grammar", "vocabulary", "reading").index(skill)) % len(options)
            arranged = list(options)
            arranged.insert(correct, arranged.pop(0))
            result.update(options=arranged, correct_option=correct)
        return result
    tiles = [dict(id=uid(f"tile-{i}"), text=token) for i, token in enumerate(model.split())]
    left = [dict(id=uid(f"left-{i}"), text=word[0]) for i, word in enumerate(words)]
    right = [dict(id=uid(f"right-{i}"), text=word[1]) for i, word in enumerate(words)]
    result = [
        item("read-choice", "multiple_choice",
             f'Which French expression means “{words[0][1]}”?' if skill == "vocabulary" else question,
             "Use the passage and glossary above.",
             options=[word[0] for word in words] if skill == "vocabulary" else choices),
        item("complete-form", "fill_blank", gap,
             GAP_INSTRUCTIONS[level][number - 1] + " Write only the missing form; keep accents.",
             {"accepted_answers": [expected]}),
        item("rebuild-line", "sentence_order", "Rebuild the model sentence in its original order.",
             f"Use every tile once to reproduce this exact model: {model}",
             dict(tiles=tiles, accepted_orders=[[tile["id"] for tile in tiles]], correct_sentence=model)),
        item("match-words", "matching", "Match each French expression with its English meaning.",
             "Use each expression and meaning once.",
             dict(left_items=left, right_items=right,
                  answer_pairs={a["id"]: b["id"] for a, b in zip(left, right)})),
        item("listen-meaning", "listening", "Listen, then choose the English meaning.",
             "Play the French audio before answering. This is listening practice, not pronunciation certification.",
             {"text_fr": model}, [translation, *LISTENING_DISTRACTORS[level][number - 1]]),
        item("recall-model", "short_answer", f"Recall the French model for: {translation}",
             f"This exact-model recall drill accepts the quoted sentence, not every valid translation: {model}",
             {"accepted_answers": [model]}),
    ]
    result[0]["explanation"] = (f"Glossary meaning: {words[0][0]} — {words[0][1]}." if skill == "vocabulary"
                                else "The answer follows from this French passage: " + row[2])
    result[3]["explanation"] = "; ".join(f"{fr} — {en}" for fr, en, _ in words)
    result[4]["explanation"] = f"French: {model}\nEnglish meaning: {translation}"
    result[5]["explanation"] = f"Exact model: {model}\nMeaning: {translation}"
    return result


def build(level, rows):
    tasks, glossary = [], []
    lengths = dict(A1="25–40", A2="50–70", B1="90–120", B2="140–180", C1="180–220", C2="220–280")
    for number, row in enumerate(rows, 1):
        module, title, reading, grammar_title, explanation, model, translation, _, _, words, _, _ = row
        glossary.extend(dict(lemma=fr, part_of_speech="phrase", translation=en, definition_french=definition)
                        for fr, en, definition in words)
        for skill in ("grammar", "vocabulary", "reading", "writing"):
            context = (f"French passage\n{reading}\n\nEnglish explanation\n{explanation}\n"
                       f"Model: {model}\nMeaning: {translation}\n\nGlossary\n" +
                       "\n".join(f"{fr} — {en}" for fr, en, _ in words) +
                       "\n\nSpeaking: retell this situation and ask two related questions. "
                       "Transcription is not a pronunciation score.")
            if skill == "writing":
                context += (f"\n\nWrite {lengths[level]} French words. "
                            + WRITING_TASKS[level][number - 1] + " Use invented personal details. "
                            "Feedback is advisory, not CEFR certification.")
            focus = {"grammar": "Identify the target form, explain its function, and contrast it with the alternative in the explanation.",
                     "vocabulary": "Read each French definition, match meanings, then use the expressions in your own example.",
                     "reading": "Find evidence for the answer in the passage. Distinguish what is stated from what is merely possible.",
                     "writing": "Plan, draft and reread for task completion, grammatical accuracy, suitable vocabulary and audience."}[skill]
            context += "\n\nLesson focus: " + focus
            task = dict(key=f"module-{number}-{skill}", skill=skill, module_title=module,
                        title=f"{title}: {skill}", objective=f"Practise {level}-targeted {skill} in the situation: {title}.",
                        context=context, vocabulary=[word[0] for word in words],
                        estimated_minutes=15 if skill == "writing" else 12,
                        exercises=[] if skill == "writing" else exercises(level, number, skill, row))
            if skill == "grammar":
                task["grammar"] = [dict(slug=f"personal-module-{number}", title=grammar_title,
                    summary=explanation, rule_code=f"personal-{level.lower()}-{number}",
                    explanation_english=explanation, examples=[(model, translation)])]
            tasks.append(task)
    return dict(version=VERSION, level=level, status="draft",
                title=f"Personal French {level}: daily life and expression",
                source_license="Original AI-assisted drafts; independent linguistic, phonetic, pedagogical, answer-key and licensing reviews pending.",
                glossary=glossary, tasks=tasks)


def main():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.assessment_content import AssessmentPack
    destination = Path(__file__).resolve().parents[1] / "content/personal"
    destination.mkdir(parents=True, exist_ok=True)
    for level, rows in DATA.items():
        body = build(level, rows)
        pack = AssessmentPack.model_validate(body)
        (destination / f"{level.lower()}-personal-{VERSION}.json").write_text(
            json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{level}: {len(pack.tasks)} draft lessons, {sum(len(t.exercises) for t in pack.tasks)} exercises")


# Original fictional situations. Not administrative, medical or legal advice.
# Rows: module, situation, reading, grammar, explanation, model, translation,
# gap, expected form, three lexical expressions, question, answer choices.
DATA = {
"A1": [
("Daily errands", "At a supermarket",
"Je suis au supermarché. Je cherche du pain et du lait. Je ne prends pas de sucre. À la caisse, je paie par carte. Je demande un reçu. Après, je vais à la boulangerie. Je prends un café à emporter et je dis : « Merci, bonne journée ! »",
"Negation with ne…pas", "Put ne before a conjugated verb and pas after it. In this example, de follows a negated indefinite quantity: pas de sucre. This does not apply to every article: je ne prends pas le bus keeps the definite article. Informal speakers often omit ne; practise the full written form.",
"Je ne prends pas de sucre.", "I do not take sugar.", "Je ne prends ___ de sucre.", "pas",
[("un reçu", "a receipt", "Un document qui confirme un paiement."), ("par carte", "by card", "Avec une carte de paiement."), ("à emporter", "to take away", "Pour consommer ailleurs, hors du magasin.")],
"What is the customer looking for at the supermarket?", ["Bread and milk", "Only sugar", "A train ticket"]),
("Getting around and asking for help", "Find the station",
"Je suis devant la mairie. Je cherche la gare. Je demande : « Excusez-moi, est-ce que le bus va à la gare ? » Une personne répond : « Oui. L’arrêt est en face de la mairie. » Je traverse au passage piéton. À pied, je peux aussi aller tout droit, puis tourner à gauche. Je remercie la personne.",
"Yes/no questions with est-ce que", "Est-ce que introduces a yes/no question without changing subject–verb order. Before a vowel, que becomes qu’: Est-ce qu’il arrive ? Practise this fixed question pattern. Start a polite request for directions with Excusez-moi.",
"Est-ce que le bus va à la gare ?", "Does the bus go to the station?", "Est-ce ___ le bus va à la gare ?", "que",
[("tout droit", "straight ahead", "Sans tourner à gauche ou à droite."), ("en face", "opposite", "De l’autre côté, devant soi."), ("à pied", "on foot", "En marchant, sans prendre de véhicule.")],
"Where is the bus stop?", ["Opposite the town hall", "Inside the bakery", "Behind the supermarket"]),
("Appointments and study", "Ask for an appointment",
"Je téléphone au secrétariat de mon université. Je dis : « Bonjour, je voudrais prendre rendez-vous. » La personne propose mardi à dix heures. Je suis disponible. Elle demande mon nom et mon adresse électronique. Je les donne. Elle dit : « Apportez votre carte d’étudiant. » Je réponds : « D’accord, merci. À mardi ! »",
"A memorised polite request", "Je voudrais + infinitive is a useful polite request. At A1, learn je voudrais as a fixed expression; study the full conditional later. Compare Je voudrais prendre rendez-vous and Je voudrais parler au secrétariat. Vous is appropriate with someone you do not know.",
"Je voudrais prendre rendez-vous.", "I would like to make an appointment.", "Je ___ prendre rendez-vous.", "voudrais",
[("prendre rendez-vous", "to make an appointment", "Fixer une date pour rencontrer une personne."), ("être disponible", "to be available", "Pouvoir venir au moment proposé."), ("une carte d’étudiant", "a student card", "Un document qui indique que son titulaire est étudiant.")],
"When is the proposed appointment?", ["Tuesday at ten", "Monday at noon", "Friday at eight"]),
],
"A2": [
("Daily life and plans", "Visit a flat",
"Nous cherchons un appartement près de l’université. L’agence nous propose une visite demain à quinze heures. Nous allons visiter l’appartement demain. Il est au troisième étage, sans ascenseur. Nous demandons si les charges sont comprises et si le quartier est calme. Après la visite, nous allons comparer les deux annonces. Nous ne prenons pas de décision tout de suite : nous voulons d’abord vérifier le budget et le temps de trajet.",
"The near future", "Use aller in the present + an infinitive to describe a plan: nous allons visiter. Conjugate aller, not the second verb. Demain clarifies when the plan will happen. Expressing a plan does not promise it will definitely occur.",
"Nous allons visiter l’appartement demain.", "We are going to visit the flat tomorrow.", "Nous ___ visiter l’appartement demain.", "allons",
[("charges comprises", "service charges included", "Avec les charges annoncées incluses dans le prix indiqué ; cela ne signifie pas que toutes les factures sont incluses."), ("un état des lieux", "a property condition report", "Une description de l’état d’un logement à un moment donné."), ("le temps de trajet", "the journey time", "La durée nécessaire pour aller d’un lieu à un autre.")],
"Why do they delay their decision?", ["To check their budget and journey time", "Because they have already signed", "Because they refuse every visit"]),
("Past experiences", "Explain yesterday’s journey",
"Hier, j’ai pris le train pour aller à une journée d’accueil. Le premier train est arrivé en retard. J’ai demandé un renseignement à un agent, puis j’ai changé de quai. Enfin, je suis arrivé à l’université. J’ai envoyé un message à mon groupe pour expliquer le retard. La visite du campus a commencé après mon arrivée. Le soir, j’ai raconté cette journée à un ami.",
"A completed past event", "The passé composé commonly presents completed events: j’ai pris. The past participle of prendre is pris. Arriver uses être here: je suis arrivé / arrivée. The ending with être agrees with the subject. Arrivé is masculine; arrivée is feminine.",
"Hier, j’ai pris le train.", "Yesterday, I took the train.", "Hier, j’ai ___ le train.", "pris",
[("en retard", "late", "Après l’heure prévue."), ("changer de quai", "to change platforms", "Aller sur un autre quai pour prendre son train."), ("un renseignement", "a piece of information", "Une information utile donnée en réponse à une question.")],
"What delayed the traveller?", ["The first train arrived late", "The campus visit was cancelled", "The traveller lost a passport"]),
("Travel and services", "Ask at a ticket office",
"À la gare, je vois deux guichets. Je choisis le guichet qui vend des billets. Je demande un aller-retour pour samedi. L’agent me propose un départ à neuf heures et un retour à dix-huit heures. Je préfère un train direct. Avant de payer, je vérifie la date et l’heure sur l’écran. L’agent explique où changer de train si je choisis une autre option. Je garde mon billet et le reçu.",
"Qui as a relative subject", "Qui replaces the subject in a relative clause: un guichet qui vend des billets. Que replaces a direct object: le billet que je garde. The verb agrees with the antecedent: des guichets qui vendent. Both pronouns can refer to things, but their grammatical functions differ.",
"C’est un guichet qui vend des billets.", "It is a ticket office that sells tickets.", "C’est un guichet ___ vend des billets.", "qui",
[("un aller-retour", "a return ticket", "Un billet pour aller à un endroit puis revenir."), ("un train direct", "a direct train", "Un train qui permet le trajet sans changer de train."), ("avant de payer", "before paying", "Avant de régler le prix demandé.")],
"What kind of train does the traveller prefer?", ["A direct train", "A train with three changes", "A train on a different date"]),
],
"B1": [
("Narrating experience", "Describe student life",
"Quand j’étais étudiant, je travaillais le soir. En général, je suivais les cours le matin et je révisais à la bibliothèque l’après-midi. Un jour, le responsable de mon équipe m’a proposé de changer mes horaires. Cette proposition m’a permis de préparer un examen important. J’ai accepté, puis j’ai expliqué ma nouvelle organisation à mes collègues. Aujourd’hui, je raconte cette expérience pour montrer comment une discussion peut résoudre un problème concret. Je distingue mes habitudes des événements précis qui ont changé la situation.",
"Past habits and events", "The imparfait can describe a repeated past situation: je travaillais le soir. The passé composé can move a story forward with a bounded event: le responsable m’a proposé. This is a choice of viewpoint, not a rule that every long action requires the imparfait. Use the explicitly requested tense in the gap.",
"Quand j’étais étudiant, je travaillais le soir.", "When I was a student, I used to work in the evenings.", "Imparfait de travailler : je ___ le soir.", "travaillais",
[("à l’époque", "at that time", "Au moment passé dont on parle."), ("changer ses horaires", "to change one’s working hours", "Modifier les heures auxquelles on travaille."), ("un événement précis", "a specific event", "Un fait particulier situé dans le récit.")],
"What helped the speaker prepare an exam?", ["A change to working hours", "Leaving university permanently", "Cancelling every course"]),
("Opinions and reasons", "Prepare for a job interview",
"Avant un entretien, je lis la présentation de l’entreprise et je prépare deux exemples de mon travail. Pendant l’échange, je présente mes compétences sans exagérer mon expérience. Je demande : « Pourriez-vous préciser les horaires ? » Je souhaite aussi connaître les tâches prioritaires et l’organisation de l’équipe. Si une question n’est pas claire, je demande une reformulation. À la fin, je résume ce que j’ai compris et j’explique pourquoi le poste m’intéresse. Je peux défendre mon point de vue tout en restant ouvert à une autre façon de travailler.",
"A polite conditional request", "Pourriez-vous + infinitive asks politely about someone’s ability or willingness to do something. Pourriez is the conditional present of pouvoir with vous. A hyphen links the inverted verb and pronoun. Politeness also depends on tone and context; a conditional form alone does not make every demand appropriate.",
"Pourriez-vous préciser les horaires ?", "Could you clarify the working hours?", "___-vous préciser les horaires ?", "Pourriez",
[("mettre en valeur", "to highlight", "Présenter clairement les points forts."), ("une reformulation", "a rephrasing", "Une autre manière d’exprimer la même idée."), ("les tâches prioritaires", "the priority tasks", "Les travaux qu’il faut traiter en premier.")],
"What does the candidate ask to clarify?", ["The working hours", "A restaurant menu", "The weather forecast"]),
("Practical problem solving", "Organise an appointment",
"Je dois rencontrer un conseiller pour discuter de mon projet d’études. Il faut que je prenne rendez-vous. Je consulte les créneaux proposés et j’en choisis un qui correspond à mes disponibilités. Dans mon message, je précise l’objet de la rencontre et je demande quels documents préparer. Si je ne peux plus venir, je préviens le service au lieu de laisser un créneau inutilisé. Cette situation est fictive : dans la vie réelle, je lis les instructions du service concerné. Mon objectif linguistique est d’exprimer une nécessité et de demander une précision.",
"A common necessity pattern", "Il faut que + a clause normally takes the subjunctive: il faut que je prenne. Prendre has the subjunctive form prenne with je. Il faut + infinitive is another structure: il faut prendre rendez-vous. Do not put an infinitive directly after il faut que.",
"Il faut que je prenne rendez-vous.", "I need to make an appointment.", "Il faut que je ___ rendez-vous.", "prenne",
[("un créneau disponible", "an available time slot", "Une période pendant laquelle un rendez-vous est possible."), ("l’objet de la rencontre", "the purpose of the meeting", "Le sujet principal que l’on souhaite aborder."), ("prévenir le service", "to notify the department", "Informer le service à l’avance d’un changement.")],
"What should the speaker do if unable to attend?", ["Notify the department", "Keep the slot without saying anything", "Send unrelated documents"]),
],
}

DATA.update({
"B2": [
("Discussion and debate", "Debate public transport",
"Une association organise une discussion sur les déplacements quotidiens. Certains participants privilégient la voiture, car ils travaillent loin des lignes régulières. D’autres défendent le train en soulignant son confort et la possibilité de lire pendant le trajet. Bien que le trajet soit long, je préfère le train. Je reconnais cependant que mon choix dépend de ma situation : une personne qui commence très tôt n’a pas forcément les mêmes possibilités. Pour débattre utilement, je distingue les contraintes individuelles des objectifs collectifs et je propose de comparer plusieurs scénarios, sans présenter une préférence personnelle comme une solution universelle.",
"Concession with bien que", "Bien que introduces a conceded fact and takes the subjunctive: bien que le trajet soit long. The subjunctive here does not mean the fact is doubtful. Même si normally takes an indicative tense: même si le trajet est long. Similar meanings do not make these grammatical patterns interchangeable.",
"Bien que le trajet soit long, je préfère le train.", "Although the journey is long, I prefer the train.", "Bien que le trajet ___ long, je préfère le train.", "soit",
[("une contrainte individuelle", "an individual constraint", "Une limite liée à la situation particulière d’une personne."), ("un objectif collectif", "a shared objective", "Un but poursuivi par plusieurs personnes ensemble."), ("nuancer son propos", "to qualify one’s statement", "Préciser les limites de ce que l’on affirme.")],
"Why does the speaker qualify the preference for trains?", ["Different people face different constraints", "The speaker says every journey is identical", "The discussion forbids alternatives"]),
("Register and nuance", "Write a formal follow-up",
"Après un entretien, je rédige un message de suivi. Je remercie mon interlocutrice et je rappelle brièvement l’objet de notre échange. Comme une information manque encore, j’écris : « J’aurais souhaité recevoir une réponse plus tôt. » Cette phrase peut exprimer un regret ou atténuer une demande selon le contexte ; elle risque aussi de paraître insistante. Je relis donc le message pour vérifier le ton et je formule clairement ce dont j’ai besoin aujourd’hui. Un registre formel ne consiste pas à multiplier les mots compliqués : il demande surtout de la précision, de la courtoisie et une organisation lisible.",
"The conditional past in context", "J’aurais souhaité combines the conditional of avoir and the past participle souhaité. It can express an unrealised wish or sometimes soften a request. Its pragmatic effect depends on context. A neutral present request is Pourriez-vous m’indiquer… ? A conditional-past sentence is not automatically polite.",
"J’aurais souhaité recevoir une réponse plus tôt.", "I would have liked to receive an answer earlier.", "J’aurais ___ recevoir une réponse plus tôt.", "souhaité",
[("un message de suivi", "a follow-up message", "Un message envoyé après un premier échange."), ("atténuer une demande", "to soften a request", "Rendre une demande moins directe dans sa formulation."), ("un registre formel", "a formal register", "Une manière de s’exprimer adaptée à un contexte officiel ou professionnel.")],
"What is the writer checking when rereading?", ["The tone and clarity of the message", "Only the number of long words", "Whether the message contains no request"]),
("Long-form communication", "Clarify a document request",
"Dans cet échange fictif, un service demande une pièce supplémentaire pour examiner un dossier. Je réponds : « Voici le document dont vous avez besoin. » Avant d’envoyer le message, je vérifie que la pièce correspond bien à la demande. Je rappelle la référence du dossier et je pose une seule question sur l’étape suivante. Le service peut ainsi comprendre rapidement le contexte sans relire tous les échanges. Pour m’exercer, je transforme ensuite le message en un résumé oral destiné à un ami. Je conserve les informations utiles, mais j’adapte le vocabulaire et le degré de formalité au destinataire.",
"Dont and a complement with de", "Avoir besoin de explains dont: le document dont vous avez besoin. Dont can replace a complement introduced by de, but not every prepositional complement. Compare le service auquel je m’adresse, from s’adresser à. Do not add a redundant de after dont in this example.",
"Voici le document dont vous avez besoin.", "Here is the document you need.", "Voici le document ___ vous avez besoin.", "dont",
[("une pièce supplémentaire", "an additional document", "Un document ajouté à ceux déjà fournis."), ("la référence du dossier", "the file reference", "Le code qui permet d’identifier un dossier."), ("l’étape suivante", "the next step", "La prochaine phase d’une démarche.")],
"Why include the file reference?", ["To identify the context quickly", "To replace the requested document", "To avoid answering the department"]),
],
"C1": [
("Complex argument", "Evaluate a university proposal",
"Un groupe de travail examine une proposition destinée à améliorer l’accueil des étudiants. Le projet présente des avantages, mais son évaluation initiale a négligé certaines contraintes. Si cette mesure avait été évaluée, nous aurions évité cet écueil. Cette hypothèse rétrospective ne suffit pourtant pas à établir une responsabilité : elle invite surtout à préciser les critères utilisés. Dans ma synthèse, je sépare les faits établis, les interprétations et les conséquences possibles. Je reconnais la force de l’argument favorable tout en discutant sa portée. Je propose enfin une phase d’expérimentation limitée, assortie de critères explicites, plutôt qu’une conclusion définitive fondée sur des données encore partielles.",
"A past counterfactual", "Si + plus-que-parfait can introduce a counterfactual past condition; the consequence often uses the conditional past: si… avait été évaluée, nous aurions évité…. Do not replace avait by aurait directly after conditional si here. A hypothetical alternative is not itself proof of causation in a real event.",
"Si cette mesure avait été évaluée, nous aurions évité cet écueil.", "If this measure had been evaluated, we would have avoided this pitfall.", "Si cette mesure avait été évaluée, nous ___ évité cet écueil.", "aurions",
[("un écueil", "a pitfall", "Une difficulté susceptible de compromettre une démarche."), ("la portée d’un argument", "the scope of an argument", "L’étendue des conclusions que cet argument permet de soutenir."), ("des données partielles", "incomplete data", "Des informations qui ne couvrent pas encore tous les aspects nécessaires.")],
"What does the speaker propose instead of a final conclusion?", ["A limited trial with explicit criteria", "Immediate generalisation without evaluation", "Removing every evaluation criterion"]),
("Professional communication", "Report a meeting accurately",
"Après une réunion, je prépare un compte rendu à destination de collègues absents. La responsable a indiqué que le dossier serait examiné. Je conserve cette relation temporelle : au moment de son intervention, l’examen était encore à venir. Je distingue les décisions prises des propositions qui restent à discuter et je précise les responsabilités annoncées sans ajouter d’engagement qui n’a pas été formulé. Lorsque mes notes ne permettent pas de restituer un point avec certitude, je le signale et je demande confirmation. Un compte rendu utile réduit l’ambiguïté ; il ne transforme pas une hypothèse en décision pour rendre le texte plus fluide.",
"Future viewed from a past reporting point", "Serait expresses a future relative to a past statement: a indiqué que… serait examiné. French reported speech does not mechanically change the tense of every sentence; temporal viewpoint and continuing validity matter. Preserve the original degree of certainty and distinguish reported information from inference.",
"La responsable a indiqué que le dossier serait examiné.", "The manager indicated that the file would be examined.", "La responsable a indiqué que le dossier ___ examiné.", "serait",
[("un compte rendu", "a meeting report", "Un texte qui restitue les éléments importants d’une réunion."), ("un engagement explicite", "an explicit commitment", "Une promesse ou une obligation clairement formulée."), ("demander confirmation", "to ask for confirmation", "Vérifier auprès d’une personne qu’une information est exacte.")],
"How does the writer handle an uncertain point?", ["Signals the uncertainty and asks for confirmation", "Presents it as a firm decision", "Deletes all other information"]),
("Style and synthesis", "Compare two viewpoints",
"Deux textes analysent une même évolution, mais ils ne répondent pas exactement à la même question. Le premier décrit des effets observés sur une période courte ; le second envisage des conséquences à plus long terme. Il semblerait que cette conclusion soit prématurée. Je n’écarte pas pour autant les observations disponibles : je précise simplement ce qu’elles permettent d’affirmer. Dans ma synthèse, je rapproche les points de convergence, puis j’explique les divergences de méthode et d’échelle. J’évite de juxtaposer des citations sans lien logique ou de donner aux deux sources un accord qu’elles n’expriment pas. La prudence linguistique sert la précision du raisonnement, et non l’absence de prise de position.",
"Careful qualification", "Il semblerait que commonly introduces a qualified judgement and takes the subjunctive here: soit. Do not generalise this to every use of sembler: construction, polarity and intended certainty affect the choice. Distinguish uncertainty about evidence from disagreement with a conclusion.",
"Il semblerait que cette conclusion soit prématurée.", "It would seem that this conclusion is premature.", "Il semblerait que cette conclusion ___ prématurée.", "soit",
[("un point de convergence", "a point of agreement", "Un aspect sur lequel plusieurs analyses se rejoignent."), ("une divergence de méthode", "a methodological difference", "Une différence dans la manière de conduire une analyse."), ("une prise de position", "a stated position", "Une opinion assumée et exprimée sur un sujet.")],
"Why does the writer qualify the conclusion?", ["The evidence does not yet justify such a broad claim", "The writer rejects every observation", "Both sources make exactly the same argument"]),
],
"C2": [
("Precision and idiom", "Examine the force of a promise",
"Dans une tribune fictive, une porte-parole promet une réforme ambitieuse. Encore faut-il que cette promesse soit suivie d’effets. La formule ne répète pas simplement une nécessité : elle met au jour la condition qui demeure en suspens derrière l’annonce. Pour autant, la réserve exprimée ne saurait tenir lieu d’évaluation. Mon commentaire distingue donc l’effet rhétorique de la promesse, les moyens effectivement annoncés et les critères qui permettraient d’en apprécier la réalisation. Je m’interdis d’attribuer à l’oratrice une intention que le texte ne permet pas d’établir. La discussion peut être incisive sans devenir péremptoire ; elle gagne en force lorsque les limites de son propre raisonnement sont rendues visibles.",
"A remaining condition and rhetorical inversion", "Encore faut-il que means roughly but it remains necessary that. In this rhetorical construction, inversion belongs to the fixed presentational pattern; que is followed by the subjunctive soit. It does not literally say an action happens again. This sustained-register pattern is suited to argument rather than an elementary request at a shop.",
"Encore faut-il que cette promesse soit suivie d’effets.", "But that promise still needs to be followed by action.", "Encore faut-il que cette promesse ___ suivie d’effets.", "soit",
[("suivi d’effets", "followed by action", "Accompagné de réalisations concrètes, et pas seulement de paroles."), ("tenir lieu de", "to serve in place of", "Remplacer quelque chose dans la fonction considérée."), ("en suspens", "unresolved", "Qui attend encore une décision ou une réponse.")],
"What does the comment distinguish?", ["Rhetorical effect, announced means and evaluation criteria", "The speaker’s private intentions as established fact", "Only the number of promises"]),
("Specialized discourse", "Acknowledge reservations precisely",
"Un comité examine plusieurs réserves concernant une méthode de travail. Quelque fondées que soient ces réserves, elles n’épuisent pas le débat. La concession reconnaît leur valeur sans leur attribuer une portée illimitée. Le rapport distingue la solidité d’une objection de son aptitude à invalider l’ensemble d’un dispositif ; il examine aussi les réponses possibles et les questions qui demeurent ouvertes. Cette situation est fictive et ne constitue pas un avis juridique ou technique. L’exercice porte sur l’articulation du raisonnement : concéder un point, circonscrire ce qu’il établit, puis maintenir une question légitime. Une reformulation accessible conserve ces nuances au lieu de réduire le propos à une opposition binaire.",
"Quelque…que in a concession", "In quelque fondées que soient ces réserves, quelque modifies the adjective and is an invariable adverb meaning however. The conceded clause takes the subjunctive soient. Contrast plural quelques in quelques réserves, where it determines a noun. Do not mechanically substitute this sustained-register pattern for every même si clause.",
"Quelque fondées que soient ces réserves, elles n’épuisent pas le débat.", "However well-founded these reservations may be, they do not settle the entire debate.", "Quelque fondées que ___ ces réserves, elles n’épuisent pas le débat.", "soient",
[("circonscrire une question", "to delimit an issue", "Définir précisément les limites de la question examinée."), ("une objection fondée", "a well-founded objection", "Une critique appuyée sur des raisons pertinentes."), ("une opposition binaire", "a binary opposition", "Une présentation qui réduit le débat à deux positions exclusives.")],
"What does acknowledging the objections avoid?", ["Treating valid reservations as an unlimited refutation", "Pretending no reservation exists", "Reducing every issue to exactly two positions"]),
("Context-sensitive expression", "Negotiate interview wording",
"Lors de la préparation d’un entretien, deux collègues discutent d’une formule destinée à résumer un désaccord. Si tant est que cette formule convienne, encore faudrait-il en préciser la portée. L’une juge l’expression trop catégorique ; l’autre craint qu’une atténuation excessive n’efface le point de divergence. Ils recherchent une formulation intelligible à un public non spécialiste, sans trahir la complexité du sujet. Une pointe d’ironie, efficace à l’oral entre collègues, pourrait sembler désobligeante dans un compte rendu. La révision consiste donc à ajuster simultanément le degré d’engagement, le registre et les présupposés. Aucune formule n’est tenue pour élégante indépendamment de son destinataire et de l’effet qu’elle produit.",
"Qualified assumptions and pragmatic scope", "Si tant est que introduces a reservation about an assumption and takes the subjunctive here: convienne. It differs from an ordinary si + indicative conditional. Encore faudrait-il adds a further qualified condition. This is cautious argument, not a recommendation to make every practical request indirect; register and the listener’s needs remain central.",
"Si tant est que cette formule convienne, encore faudrait-il en préciser la portée.", "Even assuming that this wording is suitable, its scope would still need to be clarified.", "Si tant est que cette formule ___, encore faudrait-il en préciser la portée.", "convienne",
[("le degré d’engagement", "the degree of commitment", "La force avec laquelle une personne assume une affirmation."), ("un présupposé", "a presupposition", "Un élément présenté comme déjà admis dans un énoncé."), ("une formulation catégorique", "a categorical formulation", "Une manière d’affirmer sans laisser place à une réserve.")],
"Why might irony be changed in the report?", ["Its effect depends on audience and context", "It always makes formal writing clearer", "It eliminates every disagreement"]),
],
})

if __name__ == "__main__":
    main()
