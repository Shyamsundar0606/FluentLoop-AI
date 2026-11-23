"""Author future A0/A1 releases only. Import requires a separate authorization."""
import json
from pathlib import Path
from uuid import NAMESPACE_URL,uuid5

A0 = [
    dict(key='letters-and-name',module='Meet French sounds and letters',title='Letters and your first name',
         passage='Bonjour. Je m’appelle Léa. Mon prénom commence par L.',
         explanation='A first name is a useful starting point for spelling. The French alphabet has 26 letters: A B C D E F G H I J K L M N O P Q R S T U V W X Y Z. Letter names and the sounds in words are different: do not pronounce a word by reading English letter names. Learn je m’appelle as a complete expression meaning my name is. Use an invented name here.',
         pronunciation='Listen to the whole model, repeat it, and ask the Tutor to practise spelling a name one letter at a time. Synthetic letter-name playback needs human checking; a speech transcript does not score pronunciation.',
         model='Je m’appelle Léa.',translation='My name is Léa.',gap='Je m’___ Léa.',answer='appelle',hint='Copy the missing word from the model expression je m’appelle.',
         words=[('la lettre A','the letter A','La première lettre de l’alphabet.'),('la lettre B','the letter B','La deuxième lettre de l’alphabet.'),('mon prénom','my first name','Le nom personnel utilisé avant le nom de famille.')],
         question='What is the speaker’s first name?',choices=['Léa','Marie','Paul'],distractors=['My name is Marie.','Her name is Léa.']),
    dict(key='hear-u-and-ou',module='Meet French sounds and letters',title='Hear u and ou in short phrases',
         passage='Tu es où ? — Je suis ici. Tout va bien.',
         explanation='French u and ou represent different vowel sounds in these examples: tu and tout. Hear the difference before trying to explain the grammar. Tu es où ? is a familiar spoken question meaning Where are you? Je suis ici means I am here. Practise with someone you know; tu is informal singular.',
         pronunciation='French u is /y/ and ou is /u/ in these examples. For /y/, keep the tongue near the position for /i/ while rounding the lips; /u/ has a farther-back tongue position. Listen, repeat slowly and compare by ear. These are introductory cues, not an acoustic score.',
         model='Tu es où ?',translation='Where are you?',gap='___ es où ?',answer='Tu',hint='Use the informal singular pronoun from the model question.',
         words=[('tu es où','where are you','Une question familière pour demander la position d’une personne.'),('tout va bien','everything is fine','Une expression pour dire que la situation est bonne.'),('je suis ici','I am here','Une expression pour indiquer sa propre position.')],
         question='Which reply gives the speaker’s location?',choices=['Je suis ici.','Tout va bien.','Bonjour.'],distractors=['Who are you?','Where am I?']),
    dict(key='greet-and-leave',module='First words and polite exchanges',title='Greet someone and say goodbye',
         passage='Bonjour, madame. — Bonjour ! — Au revoir, madame. — Au revoir !',
         explanation='Bonjour opens a daytime exchange. Au revoir closes it. Madame and monsieur address people politely when appropriate. Salut is familiar and can mean hi or bye; learn it with a clear context rather than assuming it suits every service encounter.',
         pronunciation='Bonjour contains a nasal vowel in bon. Do not add a separate English n after it. The final r in bonjour and au revoir is pronounced. Listen and copy the whole phrase at a comfortable speed.',
         model='Bonjour, madame.',translation='Hello, madam.',gap='___, madame.',answer='Bonjour',hint='Use the daytime greeting in the opening line, not the closing expression.',
         words=[('bonjour, madame','hello, madam','Une salutation polie pour commencer un échange.'),('au revoir, monsieur','goodbye, sir','Une formule polie pour terminer un échange.'),('salut, Léa','hi, Léa','Une salutation familière adressée ici à Léa.')],
         question='Which expression closes the exchange?',choices=['Au revoir.','Bonjour.','Madame.'],distractors=['Goodbye, madam.','Hello, sir.']),
    dict(key='first-polite-request',module='First words and polite exchanges',title='A first request at a café',
         passage='Bonjour. Un café, s’il vous plaît. — Voilà. — Merci beaucoup. Au revoir.',
         explanation='A noun phrase followed by s’il vous plaît can make a short polite request in a café. Learn the whole expression before analysing its grammar. Merci beaucoup means thank you very much. Politeness includes greeting the person and listening to the reply.',
         pronunciation='Café ends with the vowel /e/: the accent is part of the spelling, not a stress mark. Listen to the rhythm of s’il vous plaît as a group rather than inserting an English-style stress on every word.',
         model='Un café, s’il vous plaît.',translation='A coffee, please.',gap='Un café, s’il vous ___.',answer='plaît',hint='Complete the quoted polite expression and retain the circumflex accent.',
         words=[('un café, s’il vous plaît','a coffee, please','Une demande courte et polie pour commander un café.'),('merci beaucoup','thank you very much','Une expression pour remercier chaleureusement.'),('excusez-moi, madame','excuse me, madam','Une formule pour attirer poliment l’attention de son interlocutrice.')],
         question='What is ordered?',choices=['A coffee','A train ticket','A glass of milk'],distractors=['A tea, please.','Two coffees, please.']),
    dict(key='first-numbers',module='Read, type and practise safely',title='Count objects from zero to ten',
         passage='Zéro, un, deux, trois, quatre, cinq, six, sept, huit, neuf, dix. J’ai deux stylos et trois cahiers.',
         explanation='Start by recognising the numbers, then use them with a small number of objects. J’ai means I have; learn it as a fixed expression now. Deux stylos means two pens. This lesson practises quantities, not every pronunciation of a number in every context.',
         pronunciation='Some number pronunciations change with the following word. Practise deux stylos and trois cahiers as complete groups. A written final consonant is not automatically pronounced; do not invent a universal silent-letter rule.',
         model='J’ai deux stylos.',translation='I have two pens.',gap='J’ai ___ stylos.',answer='deux',hint='Write the French word for the number 2.',
         words=[('deux stylos','two pens','Deux instruments utilisés pour écrire.'),('trois cahiers','three notebooks','Trois petits livres de feuilles pour écrire.'),('zéro euro','zero euros','Une quantité de zéro dans cette monnaie.')],
         question='How many notebooks does the speaker have?',choices=['Three','Two','Ten'],distractors=['I have three pens.','I have two notebooks.']),
    dict(key='type-french-accents',module='Read, type and practise safely',title='Keep accents when typing French',
         passage='Ça va très bien. À Paris, Léa entre dans une école. Elle prend un café après le cours.',
         explanation='Accents and the cedilla belong to French spelling. Compare é in école/café, è in très/après, à in à Paris and ç in ça. Capitals retain their accents: Ça and À. Use the on-screen French character keys in written-answer exercises, or your keyboard’s French/International layout. Do not remove accents to make a spelling answer fit.',
         pronunciation='The spelling marks do not all mean the same sound. É often represents /e/ and è often represents /ɛ/; accent marks are not English stress marks. The cedilla gives ç an /s/ sound here. Listen to each complete word.',
         model='Ça va très bien.',translation='Things are going very well.',gap='___ va très bien.',answer='Ça',hint='Write Ça with its capital C and cedilla, as in the model.',
         words=[('ça va très bien','things are going very well','Une expression pour dire que tout se passe bien.'),('une école à Paris','a school in Paris','Un lieu d’enseignement situé à Paris.'),('un café à Lyon','a coffee in Lyon','Une boisson prise ici dans la ville de Lyon.')],
         question='Which spelling mark appears in Ça?',choices=['A cedilla','An acute accent','A circumflex'],distractors=['Things are going badly.','Things were going very well.']),
]


A1 = [
    dict(key='tell-the-time',module='Time and everyday arrangements',title='Understand a simple timetable',
         passage='Le cours commence à neuf heures. La pause est à dix heures. Je regarde l’horaire et je demande : « À quelle heure est le cours ? »',
         explanation='Ask À quelle heure… ? for a time. À neuf heures means at nine o’clock. Learn le cours commence as a useful phrase. In this timetable, neuf heures is the start of class and dix heures is the break; keep the two details separate.',
         model='Le cours commence à neuf heures.',translation='The class starts at nine o’clock.',gap='Le cours commence à ___ heures.',answer='neuf',hint='Write the French word for 9, the stated class starting time.',
         words=[('à neuf heures','at nine o’clock','À l’heure indiquée par le nombre neuf.'),('une pause à dix heures','a break at ten o’clock','Un moment de repos prévu à dix heures.'),('l’horaire du cours','the class timetable','Les heures prévues pour le cours.')],question='When is the break?',choices=['At ten','At nine','At noon'],distractors=['The class starts at ten o’clock.','The break starts at nine o’clock.']),
    dict(key='days-and-dates',module='Time and everyday arrangements',title='Say a day and a date',
         passage='Nous sommes le premier mai. Dans cette situation imaginaire, c’est lundi. Mardi matin, je rencontre une amie. Je note le jour et la date dans mon agenda.',
         explanation='For the first day of a month, use le premier: le premier mai. Other dates generally use a cardinal number: le deux mai. French day and month names normally take a lower-case initial. The weekday in this passage is invented, not a statement about a real calendar year.',
         model='Nous sommes le premier mai.',translation='It is the first of May.',gap='Nous sommes le ___ mai.',answer='premier',hint='Use the ordinal word used for the first day of the month.',
         words=[('le premier mai','the first of May','Le jour numéro un du mois de mai.'),('mardi matin','Tuesday morning','La matinée du mardi.'),('noter la date','to write down the date','Écrire le jour et le mois pour les garder en mémoire.')],question='When does the speaker meet a friend?',choices=['Tuesday morning','Monday evening','Friday morning'],distractors=['It is the second of May.','It is the first of June.']),
    dict(key='describe-clothes',module='Describe and build sentences',title='Agree a familiar colour adjective',
         passage='Je regarde les vêtements. La veste est bleue. Le pantalon est noir. Les chaussures sont rouges. Je choisis la veste pour sortir.',
         explanation='A colour adjective such as bleu normally agrees with the noun: une veste bleue, un manteau bleu. Rouge already ends in e in both singular genders; add s for des chaussures rouges. This small set is not a rule for every colour word: some colour expressions are invariable.',
         model='La veste est bleue.',translation='The jacket is blue.',gap='La veste est ___.',answer='bleue',hint='Use bleu agreeing with the feminine singular noun veste.',
         words=[('une veste bleue','a blue jacket','Une veste de couleur bleue.'),('un pantalon noir','black trousers','Un pantalon de couleur noire.'),('des chaussures rouges','red shoes','Des chaussures de couleur rouge.')],question='Which clothes are red?',choices=['The shoes','The jacket','The trousers'],distractors=['The jacket is black.','The trousers are blue.']),
    dict(key='negate-a-quantity',module='Describe and build sentences',title='Say what you do not have',
         passage='À la caisse, je cherche des pièces. Je n’ai pas de monnaie. Je demande : « Est-ce que je peux payer par carte ? » La personne répond oui.',
         explanation='With avoir, put ne/n’ before the verb and pas after it: je n’ai pas. An indefinite or partitive quantity often becomes de after negation: j’ai de la monnaie → je n’ai pas de monnaie. This is not a rule for every article or verb: je n’aime pas le café keeps le, and ce n’est pas un stylo keeps un.',
         model='Je n’ai pas de monnaie.',translation='I do not have any change.',gap='Je n’___ pas de monnaie.',answer='ai',hint='Use avoir in the present, je form, after the existing n’.',
         words=[('de la monnaie','some change','Des pièces ou de petites sommes pour payer.'),('chercher des pièces','to look for coins','Essayer de trouver des pièces de monnaie.'),('payer sans espèces','to pay without cash','Payer autrement qu’avec des billets ou des pièces.')],question='How does the speaker ask to pay?',choices=['By card','Only with coins','With a train ticket'],distractors=['I have some change.','I do not have a card.']),
    dict(key='locate-a-place',module='Questions and local travel',title='Locate an everyday place',
         passage='Je cherche une pharmacie. La pharmacie est près de la gare. La boulangerie est en face du parc. Je regarde le plan avant de partir.',
         explanation='Où est… ? asks where something is. Près de means near. With de + le, use du: près du parc. With a feminine article, de la remains two words: près de la gare. A location is not a direction: près de says where a place is, not which way to turn.',
         model='La pharmacie est près de la gare.',translation='The pharmacy is near the station.',gap='La pharmacie est près ___ la gare.',answer='de',hint='Complete the location expression près de.',
         words=[('près de la gare','near the station','À une faible distance de la gare.'),('en face du parc','opposite the park','De l’autre côté, devant le parc.'),('regarder le plan','to look at the map','Consulter un dessin qui indique les lieux.')],question='What is opposite the park?',choices=['The bakery','The pharmacy','The station'],distractors=['The pharmacy is far from the station.','The bakery is near the station.']),
    dict(key='ask-a-price',module='Questions and local travel',title='Ask and check a price',
         passage='Au guichet, je demande le prix. Ce billet coûte quatre euros. Je prépare cinq euros et je vérifie la monnaie. Je garde mon billet.',
         explanation='Combien coûte… ? asks the price of one item. Compare combien coûtent ces billets ? for plural tickets. In quatre euros, euros is plural. The prices in this passage are invented language-practice details, not actual fares.',
         model='Ce billet coûte quatre euros.',translation='This ticket costs four euros.',gap='Ce billet coûte ___ euros.',answer='quatre',hint='Write the French word for the stated price, 4.',
         words=[('un billet à quatre euros','a four-euro ticket','Un billet dont le prix est quatre euros.'),('payer en espèces','to pay in cash','Payer avec des billets ou des pièces.'),('vérifier la monnaie','to check the change','Contrôler la somme rendue après un paiement.')],question='How much does the ticket cost?',choices=['Four euros','Five euros','Nine euros'],distractors=['This ticket costs five euros.','These tickets cost four euros each.']),
    dict(key='a-morning-routine',module='Routines and everyday services',title='Describe a morning with a familiar verb',
         passage='Le matin, je me lève à sept heures. Je prends le petit déjeuner. À huit heures, je pars pour l’université. Le soir, je me couche tôt.',
         explanation='Learn je me lève as a complete present-tense expression meaning I get up. Me belongs to this pronominal verb with je; do not omit it. Compare je pars, where no me is needed. The verb lever changes its written vowel in je me lève. Start with this form before learning the whole pattern.',
         model='Je me lève à sept heures.',translation='I get up at seven o’clock.',gap='Je ___ lève à sept heures.',answer='me',hint='Use the pronoun belonging to se lever with je.',
         words=[('se lever tôt','to get up early','Quitter son lit de bonne heure.'),('prendre le petit déjeuner','to have breakfast','Prendre le premier repas de la journée.'),('se coucher tard','to go to bed late','Aller au lit à une heure tardive.')],question='When does the speaker leave for university?',choices=['At eight','At seven','In the evening'],distractors=['I go to bed at seven o’clock.','I get up at eight o’clock.']),
    dict(key='an-appointment-request',module='Routines and everyday services',title='Request a routine healthcare appointment',
         passage='Bonjour. Je voudrais un rendez-vous demain. — Demain, c’est complet. Mardi matin est possible. — D’accord. Pouvez-vous confirmer l’adresse du cabinet ?',
         explanation='Use a memorised polite request: je voudrais un rendez-vous. Demain means tomorrow; mardi matin names Tuesday morning. Ask for confirmation if a detail is unclear. This is a fictional routine booking exchange, not medical advice or an emergency procedure.',
         model='Je voudrais un rendez-vous demain.',translation='I would like an appointment tomorrow.',gap='Je ___ un rendez-vous demain.',answer='voudrais',hint='Use the memorised polite form je voudrais, rather than a different request verb.',
         words=[('un rendez-vous demain','an appointment tomorrow','Une rencontre prévue le jour suivant.'),('un cabinet médical','a medical practice','Un lieu où un professionnel de santé reçoit des personnes.'),('confirmer l’adresse','to confirm the address','Vérifier que l’indication du lieu est exacte.')],question='What alternative time is offered?',choices=['Tuesday morning','Tomorrow evening','Monday night'],distractors=['I would like an appointment today.','I would like to cancel tomorrow’s appointment.']),
    dict(key='go-to-a-place',module='Routines and everyday services',title='Use au, à la and aux with a destination',
         passage='Aujourd’hui, je vais au marché. Après, je vais à la bibliothèque. Un ami demande où sont les toilettes. Je montre le panneau.',
         explanation='With a destination and a definite article: à + le becomes au, à + les becomes aux, while à la stays separate. Compare au marché, à la bibliothèque, aux toilettes. These are not rules for every country/place expression; learn the current examples before adding other patterns.',
         model='Je vais au marché.',translation='I am going to the market.',gap='Je vais ___ marché.',answer='au',hint='Combine à + le before the masculine singular noun marché.',
         words=[('au marché','to the market','Vers le lieu où des commerçants vendent leurs produits.'),('à la bibliothèque','to the library','Vers un lieu où l’on peut consulter ou emprunter des livres.'),('aux toilettes','to the toilets','Vers le lieu indiqué pour les toilettes.')],question='Where does the speaker go after the market?',choices=['To the library','To the station','To a restaurant'],distractors=['I am coming from the market.','I am going to the library.']),
    dict(key='ask-someone-to-repeat',module='Routines and everyday services',title='Keep a conversation going when you do not understand',
         passage='Je ne comprends pas la phrase. Je demande : « Pouvez-vous répéter, s’il vous plaît ? » La personne parle plus lentement. Je dis merci et je vérifie un mot : « Comment ça s’écrit ? »',
         explanation='Pouvez-vous répéter… ? is a useful memorised request. Vous is polite or plural. A hyphen links pouvez and vous in this inverted question. Ask plus lentement for slower speech. Repetition and spelling are ways to repair communication, not signs that you must stop practising.',
         model='Pouvez-vous répéter, s’il vous plaît ?',translation='Could you repeat, please?',gap='Pouvez-vous ___, s’il vous plaît ?',answer='répéter',hint='Write the infinitive répéter, keeping both acute accents.',
         words=[('plus lentement','more slowly','À une vitesse moins grande.'),('je ne comprends pas','I do not understand','Une expression pour signaler une difficulté à comprendre.'),('comment ça s’écrit','how is that spelled','Une question pour demander les lettres d’un mot.')],question='What does the other person do after the request?',choices=['Speaks more slowly','Leaves without answering','Changes the meeting date'],distractors=['Could you write, please?','Could you speak faster, please?']),
]


def activities(row,release,number):
    def uid(name):return str(uuid5(NAMESPACE_URL,f'fluentloop:{release}:{row["key"]}:{name}'))
    def item(key,kind,prompt,instructions,data=None,options=None,explanation=None):
        result=dict(key=key,type=kind,prompt=prompt,instructions=instructions,data=data or {},explanation=explanation or row['explanation'])
        if options:
            correct=number%3;labels=list(options);labels.insert(correct,labels.pop(0));result.update(options=labels,correct_option=correct)
        return result
    tiles=[dict(id=uid(f'tile-{i}'),text=word) for i,word in enumerate(row['model'].split())]
    left=[dict(id=uid(f'left-{i}'),text=fr) for i,(fr,_,_) in enumerate(row['words'])]
    right=[dict(id=uid(f'right-{i}'),text=en) for i,(_,en,_) in enumerate(row['words'])]
    return [
        item('read-detail','multiple_choice',row['question'],'Find the answer in the short French passage.',options=row['choices'],explanation='Passage: '+row['passage']),
        item('complete-model','fill_blank',row['gap'],row['hint'],dict(accepted_answers=[row['answer']])),
        item('rebuild-model','sentence_order','Rebuild this exact model: '+row['model'],'Use every tile once in the quoted model order.',dict(tiles=tiles,accepted_orders=[[t['id'] for t in tiles]],correct_sentence=row['model'])),
        item('match-meaning','matching','Match the expressions and meanings.','Use each meaning once.',dict(left_items=left,right_items=right,answer_pairs={a['id']:b['id'] for a,b in zip(left,right)}),explanation='; '.join(f'{fr} — {en}' for fr,en,_ in row['words'])),
        item('listen-meaning','listening','Listen, then choose the English meaning.','Play the French audio before answering.',dict(text_fr=row['model']),[row['translation'],*row['distractors']],explanation=row['model']+' — '+row['translation']),
        item('copy-model','short_answer','Write the quoted French model for: '+row['translation'],'Exact-model spelling practice: '+row['model'],dict(accepted_answers=[row['model']]),explanation=row['model']),
    ]


def build_a0():
    tasks=[];words={};previous=None
    for number,row in enumerate(A0,1):
        for fr,en,definition in row['words']:
            words[fr]=dict(lemma=fr,part_of_speech='phrase',translation=en,definition_french=definition)
        context=(f"Start here\n{row['passage']}\n\nUnderstand\n{row['explanation']}\n\nHear and say\n{row['pronunciation']}\n"
                 f"Model: {row['model']}\nMeaning: {row['translation']}\n\nGlossary\n"+
                 '\n'.join(f'{fr} — {en}' for fr,en,_ in row['words'])+
                 '\n\nPractise: listen, point to the matching words, then say the model. Ask the Tutor to repeat slowly. Review the previous model before continuing. No CEFR or pronunciation score is awarded.')
        task=dict(key=row['key'],skill='vocabulary' if number%2 else 'reading',module_title=row['module'],title=row['title'],
                  objective='Recognise, understand, type and say this short model: '+row['model'],context=context,
                  estimated_minutes=15,vocabulary=[fr for fr,_,_ in row['words']],exercises=activities(row,'a0-0.3.0',number),
                  prerequisites=[previous] if previous else [])
        tasks.append(task);previous=row['key']
    tasks.append(dict(key='first-two-lines',skill='writing',module_title='Read, type and practise safely',
        title='Write your first two friendly lines',objective='Combine a greeting, an invented name and a polite closing using the models already practised.',
        context='Write two short lines to an imaginary classmate. Start with Bonjour, give an invented first name using Je m’appelle, then finish with Merci or Au revoir. Copy accents carefully. Example: Bonjour. Je m’appelle Léa. Merci et au revoir. Use your own invented name; do not share personal details. Reread: is the greeting present, is the name clear, and is the closing suitable? Optional AI feedback is advisory, not a CEFR or pronunciation score.',
        vocabulary=[],exercises=[],estimated_minutes=15,prerequisites=[previous]))
    return dict(version='0.3.0',level='A1',learning_stage='A0',status='draft',title='A0: French from absolutely zero',
        source_license='Original AI-assisted introductory drafts; independent linguistic, phonetic, pedagogical, answer-key and licensing reviews pending.',
        glossary=list(words.values()),tasks=tasks)


def build_a1():
    tasks=[];words={};previous=None
    for number,row in enumerate(A1,1):
        for fr,en,definition in row['words']:
            words[fr]=dict(lemma=fr,part_of_speech='phrase',translation=en,definition_french=definition)
        context=(f"Read\n{row['passage']}\n\nUnderstand\n{row['explanation']}\n\nModel: {row['model']}\nMeaning: {row['translation']}\n\nGlossary\n"+
                 '\n'.join(f'{fr} — {en}' for fr,en,_ in row['words'])+
                 '\n\nSpeak: retell the situation with an invented detail and ask the Tutor one follow-up question. Listen to the reply and request clarification if needed. Review the previous lesson model and your saved mistakes. Feedback is practice evidence, not CEFR certification.')
        task=dict(key=row['key'],skill='vocabulary' if number%2 else 'reading',module_title=row['module'],title=row['title'],
             objective='Understand and use the target expression in a short everyday exchange: '+row['model'],context=context,estimated_minutes=20,
             vocabulary=[fr for fr,_,_ in row['words']],exercises=activities(row,'a1-0.3.2',number),prerequisites=[previous] if previous else [])
        if number in (3,4,5,7,9,10):
            task['skill']='grammar'
            task['grammar']=[dict(slug='foundation-'+row['key'],title=row['title'],summary=row['explanation'],
                rule_code='foundation-'+row['key'],explanation_english=row['explanation'],examples=[(row['model'],row['translation'])])]
        tasks.append(task)
        previous=row['key']
    tasks.extend([
        dict(key='write-a-meeting-message',skill='writing',module_title='Time and everyday arrangements',title='Write a clear meeting message',
             objective='Give a day, time and place and ask for confirmation in a short message.',
             context='Write 30–50 French words to an imaginary classmate. Suggest a day, time and meeting place. Ask whether the arrangement is suitable. Include a greeting and closing. Use invented details, not personal addresses. Reread: are the day and time consistent, are the words spelled with accents, and is the request clear? Optional AI feedback is advisory; no automatic CEFR level is awarded.',
             vocabulary=[],exercises=[],estimated_minutes=20,prerequisites=['tell-the-time','days-and-dates']),
        dict(key='a-day-and-a-request',skill='writing',module_title='Routines and everyday services',title='Describe your day and solve one small problem',
             objective='Connect a simple routine with one practical request and a response.',
             context='Write 40–60 French words about an imaginary day. Give two routine activities and their times. Add one small problem, such as not understanding a word or needing a routine appointment, and write a polite request. Use language from earlier lessons. Check present verb forms, articles, negation and accents. Then read the text aloud and practise a follow-up with the Tutor. Feedback is advisory; transcription is not pronunciation scoring.',
             vocabulary=[],exercises=[],estimated_minutes=20,prerequisites=[previous])])
    return dict(version='0.3.2',level='A1',status='draft',title='A1: everyday foundations and communication',
        source_license='Original AI-assisted A1 development drafts; independent linguistic, phonetic, pedagogical, answer-key and licensing reviews pending.',
        glossary=list(words.values()),tasks=tasks)


if __name__=='__main__':
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from app.assessment_content import AssessmentPack
    folder=Path(__file__).resolve().parents[1]/'content/foundations';folder.mkdir(exist_ok=True)
    for filename,body in [('a0-foundations-0.3.0.json',build_a0()),('a1-foundations-0.3.2.json',build_a1())]:
        pack=AssessmentPack.model_validate(body)
        (folder/filename).write_text(pack.model_dump_json(indent=2)+'\n',encoding='utf-8')
        print(f'Staged {filename}: {len(pack.tasks)} lessons, {sum(len(t.exercises) for t in pack.tasks)} exercises; no database import.')
