"""Original scenario drafts. Generates source only; never connects to a database."""
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

ROWS = [
 dict(stage='A0',version='0.4.7',title='At the bakery: point, ask, thank',
  passage='— Bonjour, madame. Une baguette, s’il vous plaît.\n— Voilà.\n— Merci. Au revoir !\n— Au revoir !',
  teaching='Learn une baguette as a whole group: a baguette. S’il vous plaît makes this short request polite. Voilà accompanies handing something over here. First greet, then ask, then thank. Point to the phrase while listening. No analysis of every word is needed yet.',
  questions=[('What does the customer request?',['One baguette','Two coffees','A train ticket']),('Which line thanks the seller?',['Merci.','Voilà.','Bonjour.'])],
  audio='Bonjour. Une baguette, s’il vous plaît. Merci.',audio_question='What is the customer doing?',audio_choices=['Making a polite request','Giving a street address','Introducing a friend'],
  words=[('une baguette','a baguette'),('s’il vous plaît','please'),('merci','thank you')],
  outcome='Recognise a greeting, one object and a polite request, and reproduce the exchange with help.',
  grammar='Memorise une baguette and the request as chunks; do not generalise noun gender from this example.',
  writing='Write three short lines for an imaginary bakery visit: a greeting, a request for une baguette, and thanks. Use the displayed model if needed. Then say the three lines aloud, slowly. This is supported retrieval, not an independent-level exam.',
  speaking='Ask the Tutor to act as a patient bakery seller. Use only the model phrases and request a slow repeat.',
  review='Hide the model and recall Bonjour, s’il vous plaît and Merci tomorrow; reopen it if needed.'),
 dict(stage='A1',version='0.4.1',title='Buy fruit at a market',
  passage='— Bonjour. Je voudrais deux pommes et un kilo de tomates, s’il vous plaît.\n— Les pommes rouges ou les vertes ?\n— Les rouges. Combien ça coûte ?\n— Cinq euros en tout.\n— Voilà. Merci et bonne journée !',
  teaching='Je voudrais is a useful polite request learned as a chunk here. Deux pommes counts items; un kilo de tomates gives a measured quantity. Les rouges refers back to les pommes. En tout introduces the total, not a price per kilo.',
  questions=[('Which apples does the customer choose?',['Red apples','Green apples','No apples']),('What does cinq euros en tout refer to?',['The whole purchase','Each apple','Only one tomato'])],
  audio='Je voudrais deux pommes et un kilo de tomates. Cinq euros en tout.',audio_question='How many apples are requested?',audio_choices=['Two','One kilo of apples','Five'],
  words=[('un kilo de tomates','a kilo of tomatoes'),('en tout','in total'),('combien ça coûte','how much does it cost')],
  outcome='Separate count, weight and total price and ask for clarification in a short purchase.',
  grammar='After a measured quantity use de: un kilo de tomates. In les rouges, the adjective agrees with the understood plural feminine pommes.',
  writing='Write 35–50 French words as a market dialogue. Request two familiar items, specify one quantity and ask the total. Invent a consistent price. Include a greeting and thanks; check de after kilo. Then perform both roles aloud.',
  speaking='Ask the Tutor to sell fruit and offer two colours. State a quantity, choose one and ask the price; request repetition once.',
  review='Recall the quantity without looking, then vary only the number. Review saved spelling mistakes before repeating.'),
 dict(stage='A2',version='0.4.2',title='Explain a delayed journey',
  passage='Hier, Lina devait rejoindre une amie à Tours. À la gare, elle a appris que son train avait vingt minutes de retard. Elle a envoyé un message : « Je suis encore à la gare. Ne m’attends pas devant le cinéma ; retrouve-moi au café à dix-huit heures. » Finalement, le train est parti avec dix minutes de retard seulement. Lina est arrivée avant l’heure proposée, mais elle n’a pas changé le rendez-vous.',
  teaching='Track the original delay, the actual delay and the new meeting arrangement separately. Devait presents an earlier plan; a appris and a envoyé move the story forward. Finalement signals the outcome, not necessarily a late arrival at the meeting.',
  questions=[('Where should the friend meet Lina?',['At the café','Outside the cinema','On the platform']),('What actually happened to the train?',['It left ten minutes late','It left twenty minutes early','It was cancelled'])],
  audio='Je suis encore à la gare. Retrouve-moi au café à dix-huit heures. Ne m’attends pas devant le cinéma.',audio_question='Which instruction is given?',audio_choices=['Meet at the café at six','Wait outside the cinema at six','Cancel the evening'],
  words=[('avoir du retard','to be late'),('finalement','in the end'),('le rendez-vous','the meeting arrangement')],
  outcome='Understand a short disruption narrative and communicate an updated plan with consistent times.',
  grammar='Use a simple past event to explain a change and a clear present instruction for the current arrangement. Do not treat every past event as background.',
  writing='Write 70–90 French words to a friend: explain an invented transport delay, distinguish the announced and actual problem, and propose a place and time. Add one clarification question. Check the sequence and reread all times.',
  speaking='Explain a delayed journey to the Tutor as your friend. Confirm the new place and time and answer a follow-up question.',
  review='Retell the events in three steps without the text, then compare the actual delay and appointment details.'),
 dict(stage='B1',version='0.4.3',title='Resolve a housing repair misunderstanding',
  passage='Quand Samir a signalé une fuite sous l’évier, l’agence lui a proposé un passage mardi matin. Il a accepté, puis a demandé si le technicien pouvait prévenir une demi-heure avant son arrivée. L’agence a répondu : « Nous transmettons votre demande. » Mardi, personne n’a appelé. Samir est donc parti travailler et a trouvé, le soir, un avis de passage. Il reconnaît qu’aucune confirmation d’appel ne lui avait été donnée, mais estime que la réponse de l’agence prêtait à confusion. Il souhaite un nouveau créneau et une confirmation écrite des modalités, plutôt qu’accuser le technicien d’avoir manqué un rendez-vous.',
  teaching='Distinguish a request being forwarded from a commitment being accepted. The narrative acknowledges Samir’s assumption while explaining his dissatisfaction. Prêter à confusion evaluates clarity; it does not prove deliberate deception.',
  questions=[('What had the agency explicitly promised?',['To pass on the request','That the technician would call','A free repair that evening']),('Which response best fits Samir’s stated aim?',['Ask for another slot and written arrangements','Accuse the technician of lying','Claim no visit ever occurred'])],
  audio='Nous transmettons votre demande. Je peux vous proposer jeudi après-midi, mais je dois encore confirmer le passage avec le technicien.',audio_question='What remains uncertain?',audio_choices=['The technician’s visit is not yet confirmed','The agency refuses every visit','Thursday has already been cancelled'],
  words=[('un créneau','a time slot'),('prêter à confusion','to be liable to cause confusion'),('un avis de passage','a notice of an attempted visit')],
  outcome='Explain a misunderstanding, acknowledge uncertainty and request a practical solution without unsupported accusations.',
  grammar='Use avait été donnée to locate a missing confirmation before the later discovery; plutôt que contrasts possible responses. Retain who said or assumed each claim.',
  writing='Write 140–170 French words to the agency. State the sequence, acknowledge what was not confirmed, explain the effect and request a new slot with written conditions. Avoid inventing legal rights. Check tone, chronology and ownership of claims.',
  speaking='Negotiate a new repair slot with the Tutor as the agency. Explain your assumption, accept one limitation and obtain an explicit confirmation.',
  review='Retell using request, response, assumption and consequence. Reuse two expressions in a different service problem.'),
 dict(stage='B2',version='0.4.4',title='Evaluate a university access proposal',
  passage='Une université envisage de fermer sa bibliothèque une heure plus tôt pour financer davantage de ressources numériques. Le conseil souligne que les entrées après vingt heures ne représentent que 6 % des visites. Une association étudiante conteste toutefois l’usage de ce chiffre : une faible fréquentation ne dit rien de l’importance du service pour ceux qui travaillent en journée. Elle demande une expérimentation pendant les examens et un relevé des usages, plutôt qu’un abandon définitif du projet. La direction accepte d’étudier cette proposition, à condition que les coûts de sécurité soient inclus. Le débat porte donc moins sur l’intérêt du numérique que sur la répartition des contraintes. Présenter l’opposition comme un refus de toute modernisation ferait disparaître la question centrale : quels étudiants supporteraient l’économie réalisée ?',
  teaching='Separate the statistic from the conclusion attributed to it. The association proposes a conditional trial, not a blanket rejection. Identify the distributional argument and the director’s cost condition before taking a position.',
  questions=[('What limitation of the statistic is raised?',['Visit share does not measure importance for affected students','The percentage proves all visits are unnecessary','The association says there are no evening visitors']),('Which summary avoids a false opposition?',['Test the proposal while evaluating access and security costs','Students reject all digital resources','The direction has cancelled its proposal'])],
  audio='Nous ne rejetons pas le numérique. Encore faudrait-il savoir qui perd un lieu de travail. Essayons pendant les examens, sans oublier le coût de la sécurité.',audio_question='What is the speaker’s position?',audio_choices=['A conditional trial with attention to affected users','Unconditional support for closure','Refusal to discuss any cost'],
  words=[('la répartition des contraintes','the distribution of burdens'),('à condition que','provided that'),('une expérimentation','a trial implementation')],
  outcome='Evaluate the limits of quantitative evidence and argue for a qualified policy option with a counterargument.',
  grammar='À condition que introduces a condition with the subjunctive. Encore faudrait-il frames an unmet requirement. A concession does not cancel the following objection.',
  writing='Write 230–280 French words for the university council. Compare two options, analyse what the 6 % figure establishes and does not establish, address security costs and propose an evaluable trial. Attribute claims and include a substantive counterargument. No external statistic may be invented.',
  speaking='Defend a conditional recommendation to the Tutor as a council member. Respond to a cost objection and distinguish your inference from the supplied evidence.',
  review='Summarise the opposing position fairly before giving your own. Revisit one overstatement and rewrite it with an explicit condition.'),
 dict(stage='C1',version='0.4.5',title='Mediate conflicting evidence about a work pilot',
  passage='Note A : après six mois de semaine aménagée, le taux d’absence a baissé dans les équipes volontaires. Les auteurs y voient un indice encourageant, tout en rappelant que les participants avaient déjà moins d’absences que la moyenne.\nNote B : les délais de réponse ont augmenté dans deux services. Le rapport précise cependant que leur nouvel outil de suivi comptabilise désormais des demandes auparavant ignorées.\nLors de la réunion, la directrice résume : « Nous disposons enfin de chiffres, mais pas encore d’une comparaison à périmètre constant. » Un représentant répond que différer toute décision reviendrait à faire du doute une politique. Tous deux souhaitent une évaluation plus solide ; ils divergent sur le coût de l’attente. Une synthèse fidèle ne saurait transformer cette divergence pratique en opposition entre science et intuition, ni fondre des indicateurs hétérogènes dans un bilan prétendument unique.',
  teaching='Track selection effects, measurement changes and the different consequences of uncertainty. Do not infer causation from the absence trend or a real deterioration solely from newly counted requests. Preserve the practical disagreement in mediation.',
  questions=[('Why is the absence result insufficient to establish a causal effect?',['Volunteers already differed from the average','All absences were measured incorrectly','The pilot lasted no time at all']),('Where do the two speakers chiefly diverge?',['On the cost of delaying action under uncertainty','On whether evaluation has any value','On whether figures exist'])],
  audio='Je ne demande pas qu’on renonce à mesurer. Je demande que l’attente soit, elle aussi, traitée comme un choix dont il faut justifier le coût.',audio_question='Which inference is warranted?',audio_choices=['The speaker challenges the presumed neutrality of delay','The speaker rejects evidence as useless','The speaker claims the pilot’s success is proved'],
  words=[('à périmètre constant','on a like-for-like scope'),('un indicateur hétérogène','an indicator unlike the others in nature'),('un biais de sélection','a selection bias')],
  outcome='Synthesise conflicting methodological evidence while preserving qualifications and the underlying decision trade-off.',
  grammar='Ne saurait marks a strongly qualified impossibility in formal prose. Ni… ni… coordinates exclusions. Distinguish reported stance from the narrator’s evaluation.',
  writing='Write a 320–380-word French decision brief synthesising both notes. Explain the two distinct comparability problems, the cost-of-waiting dispute and a conditional next step. Then append a 60-word plain-language summary for staff. Preserve uncertainty without using it to avoid every decision.',
  speaking='Mediate the disagreement with the Tutor playing both stakeholders in turn. Reformulate each fairly, then explain your conditional recommendation under questioning.',
  review='Underline every causal claim and identify its evidential basis. Rewrite one technical passage for a non-specialist without losing its qualification.'),
 dict(stage='C2',version='0.4.6',title='Interpret an institutional promise and its irony',
  passage='Dans une tribune fictive, une ville promet de rendre les démarches administratives « enfin invisibles ». L’éditorialiste salue cette « remarquable disparition » : le guichet, note-t-elle, a effectivement disparu avant les justificatifs. Elle ne regrette pas pour autant chaque formulaire papier. Son ironie vise le glissement par lequel la commodité annoncée devient une obligation de se débrouiller seul.\nLa réponse municipale assure qu’un accompagnement demeure disponible « pour ceux qui en feraient la demande ». Cette réserve ne prouve pas que l’aide soit refusée ; elle suppose néanmoins que les personnes concernées sachent identifier le dispositif et formuler leur besoin. L’éditorialiste pourrait donc reconnaître une amélioration réelle sans retirer son objection : une procédure peut être plus rapide pour ses usagers habituels et moins accessible à ceux qu’elle prétend inclure.\nMédier ces textes exige de restituer leur dissymétrie : l’un conteste les présupposés d’une promesse, l’autre décrit une possibilité formelle. Les opposer comme deux constats empiriques équivalents, ou convertir l’ironie en accusation de fraude, serait leur faire dire davantage qu’ils ne disent.',
  teaching='Analyse the target and limits of the irony, the presupposed agency in the conditional clause, and the asymmetry between an accessibility objection and an availability claim. Neither a factual exclusion nor deliberate fraud is established by these fictional excerpts.',
  questions=[('What does remarquable disparition ironically target?',['Removal of the counter without removal of the user’s burden','Proof that all paperwork has ended','A demand to restore every paper form']),('Which mediation preserves the texts’ logical scope?',['Formal availability does not settle practical accessibility','The reply proves that all users receive help','The editorial establishes intentional fraud'])],
  audio='Il serait commode de conclure que rien n’a changé. Plus commode encore d’en déduire que tout est réglé. Entre ces deux facilités demeure la question de savoir qui doit désormais rendre la procédure praticable.',audio_question='What does the parallel phrasing principally do?',audio_choices=['Reject two easy conclusions and redirect attention to the transferred burden','Assert that no improvement occurred','Certify universal accessibility'],
  words=[('se débrouiller seul','to manage on one’s own'),('une possibilité formelle','a possibility that exists in formal terms'),('le présupposé','the presupposition')],
  outcome='Explain irony, presupposition and unequal argumentative scope, then mediate for audiences with different needs.',
  grammar='Pour ceux qui en feraient la demande presents a hypothetical request; it does not entail that requests were refused. Sans retirer son objection preserves a concession’s limits. Attend to parallelism and modal commitment.',
  writing='Write a 420–500-word French critical synthesis explaining the irony, implicit assumptions and asymmetry of the two excerpts. Concede a possible improvement without inventing evidence. Then produce an 80-word neutral service explanation for a reader unfamiliar with administrative language. Explain one deliberate change of register and what nuance it preserves.',
  speaking='Defend your interpretation with the Tutor as a sceptical editor. Offer an alternative reading, delimit its plausibility and reformulate your synthesis without irony for a service user.',
  review='Compare your interpretation against exact textual evidence. Remove one over-interpretation, then reintroduce the justified nuance in two different registers.'),
]


def build(row):
    stage=row['stage']; level='A1' if stage=='A0' else stage
    identity=f"scenario-{stage}-{row['version']}"
    exercises=[]
    for index,(prompt,choices) in enumerate(row['questions']):
        position=index%3;options=list(choices);options.insert(position,options.pop(0))
        exercises.append(dict(key=f'read-{index+1}',type='multiple_choice',prompt=prompt,
            instructions='Read the French passage. Choose the claim supported by this text, not a broader assumption.',
            options=options,correct_option=position,explanation='The supported interpretation is: '+choices[0]+'. '+row['teaching']))
    exercises.append(dict(key='listen-stance',type='listening',prompt=row['audio_question'],
        instructions='Listen before answering. The audio is an original scripted excerpt; synthetic playback is not an authentic multi-speaker recording.',
        data=dict(text_fr=row['audio']),options=row['audio_choices'][1:]+row['audio_choices'][:1],correct_option=2,
        explanation=row['audio']+' — '+row['audio_choices'][0]))
    def uid(label):return str(uuid5(NAMESPACE_URL,identity+'-'+label))
    left=[dict(id=uid(f'l{i}'),text=fr) for i,(fr,_) in enumerate(row['words'])]
    right=[dict(id=uid(f'r{i}'),text=en) for i,(_,en) in enumerate(row['words'])]
    exercises.append(dict(key='lexical-scope',type='matching',prompt='Match expressions with their contextual meanings.',
        instructions='Match the meaning used in this scenario; these are not exhaustive dictionary definitions.',
        data=dict(left_items=left,right_items=list(reversed(right)),answer_pairs={a['id']:b['id'] for a,b in zip(left,right)}),
        explanation='; '.join(fr+' — '+en for fr,en in row['words'])))
    context=row['passage']+'\n\nUnderstand: '+row['teaching']+'\n\nLanguage: '+row['grammar']
    # Speaking/retrieval instructions belong to the linked transfer task. Keep
    # the passage intact within the established bounded lesson-section schema.
    tasks=[dict(key='interpret-scenario',skill='reading',title=row['title'],objective=row['outcome'],
        context=context,module_title=row['title'],estimated_minutes=20 if stage in ('A0','A1') else 35,
        vocabulary=[fr for fr,_ in row['words']],exercises=exercises),
        dict(key='transfer-and-review',skill='writing',title='Transfer and review: '+row['title'],objective=row['outcome'],
        context=row['writing']+'\n\nSpeaking transfer: '+row['speaking']+'\n\nRevision: '+row['review']+
        '\n\nSelf-review: check task fulfilment, evidence, sequence, grammar and spelling. Save a revised version after feedback. AI feedback is advisory; this module check is not a calibrated diagnostic or CEFR level-end examination.',
        module_title=row['title'],estimated_minutes=25 if stage in ('A0','A1','A2') else 45,
        prerequisites=['interpret-scenario'],exercises=[])]
    body=dict(version=row['version'],level=level,status='draft',title=stage+' scenario: '+row['title'],
        source_license='Original AI-assisted scenario drafts. Independent human language, pedagogy, answer-key and CEFR calibration reviews pending.',
        glossary=[dict(lemma=fr,part_of_speech='phrase',translation=en,
            definition_french='Mot pour exprimer sa gratitude.' if fr=='merci' else 'Dans ce contexte : '+fr+'.')
            for fr,en in row['words']],tasks=tasks)
    if stage=='A0':body['learning_stage']='A0'
    return body


if __name__=='__main__':
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from app.assessment_content import AssessmentPack
    folder=Path(__file__).resolve().parents[1]/'content/scenarios';folder.mkdir(exist_ok=True)
    for row in ROWS:
        pack=AssessmentPack.model_validate(build(row))
        (folder/f"{row['stage'].lower()}-scenarios-{row['version']}.json").write_text(pack.model_dump_json(indent=2)+'\n',encoding='utf-8')
    print('Staged 14 scenario lessons, 28 objective exercises and seven open transfer tasks; no database import.')
