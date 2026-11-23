"""Author the progressive curriculum map; never connect to a database."""
import json
from pathlib import Path

# Title, measurable outcome, available source references. Empty references are gaps.
CURRICULUM = {
    "A0": [
        ("Meet French sounds and letters", "Recognise the alphabet, distinguish a few French sounds and spell an invented first name.", ['m10-assessments-a1-0.3.0-letters-and-name','m10-assessments-a1-0.3.0-hear-u-and-ou']),
        ("First words and polite exchanges", "Greet someone, say an invented name and use a memorised polite request.", ['m10-assessments-a1-0.3.0-greet-and-leave','m10-assessments-a1-0.3.0-first-polite-request']),
        ("Read, type and practise safely", "Read simple signs, type French accents and record/review one short phrase.", ['m10-assessments-a1-0.3.0-first-numbers','m10-assessments-a1-0.3.0-type-french-accents','m10-assessments-a1-0.3.0-first-two-lines']),
    ],
    "A1": [
        ("Sounds, greetings and politeness", "Recognise common spelling patterns and open/close a short exchange.", ["a1-001", "a1-002"]),
        ("Identity, numbers, dates and time", "Give an invented name/age and ask simple personal questions.", ["a1-003", "a1-004"]),
        ("Build a first sentence", "Choose an article and subject pronoun and use a present form of être.", ["a1-005", "a1-006"]),
        ("People, possession and description", "Describe family and possessions with avoir and basic agreement.", ["a1-007", "a1-008"]),
        ("Routine and present verbs", "Describe an ordinary day and ask about another person's routine.", ["a1-009"]),
        ("Food, prices and shopping", "Find familiar items, request an order and understand a simple price.", ["a1-010", 1]),
        ("Transport and directions", "Ask where a place is and follow a short set of directions.", [2]),
        ("Appointments and study", "Request a time, state availability and check the details.", [3]),
        ("A1 cumulative review", "Combine greetings, simple questions and short written/spoken messages in a new situation.", []),
    ],
    "A2": [
        ("Plans and housing", "Arrange a viewing and compare practical constraints using near-future plans.", [1]),
        ("Past events and journeys", "Describe a completed journey and explain a delay in sequence.", [2]),
        ("Travel services and relative clauses", "Specify travel preferences and link information with qui/que.", [3]),
        ("Describe, compare and quantify", "Compare people/places and express quantities with suitable pronouns.", []),
        ("Health and everyday appointments", "Describe a simple non-emergency problem and ask for an appointment or clarification.", []),
        ("Messages and social arrangements", "Understand and write invitations, apologies and short explanations.", []),
        ("Routine listening and interaction", "Extract key details from a short exchange and repair a misunderstanding.", []),
        ("A2 cumulative review", "Handle a new everyday problem across reading, listening, writing and speaking.", []),
    ],
    "B1": [
        ("Narrate experience", "Distinguish past habits, background and bounded events in a connected story.", [1]),
        ("Work, reasons and opinions", "Explain interest in a role and ask polite follow-up questions.", [2]),
        ("Necessity and practical problems", "Explain a need, request clarification and propose a workable next step.", [3]),
        ("Hypotheses and future consequences", "Describe realistic and hypothetical alternatives with reasons.", []),
        ("Connected speech and pronouns", "Maintain a clear reference chain and link contrasting ideas.", []),
        ("News and longer conversations", "Identify main points, details and speaker positions in familiar material.", []),
        ("Personal and formal writing", "Write a coherent account and adapt a request to its recipient.", []),
        ("B1 cumulative review", "Explain a new problem, justify a choice and respond to a follow-up.", []),
    ],
    "B2": [
        ("Debate and concession", "Defend an option, acknowledge constraints and formulate a qualified compromise.", [1]),
        ("Formal requests and tone", "Compare formulations and revise an unnecessarily insistent message.", [2]),
        ("Documents and precise reference", "Clarify a document request and adapt the same information for two audiences.", [3]),
        ("Complex clauses and hypotheses", "Control relative clauses, concession and hypothetical consequences in context.", []),
        ("Extended reading and listening", "Infer a stance, distinguish evidence from assertion and compare arguments.", []),
        ("Structured argument in writing", "Develop a supported argument, address an objection and revise cohesion.", []),
        ("Negotiation and sustained speaking", "Negotiate alternatives and maintain an extended exchange with clarification.", []),
        ("B2 cumulative review", "Respond to an unfamiliar dossier through supported written and spoken argument.", []),
    ],
    "C1": [
        ("Evaluate evidence and alternatives", "Separate evidence, retrospective hypothesis and causal inference.", [1]),
        ("Report professional discussion", "Preserve temporal viewpoint and distinguish commitments from unresolved points.", [2]),
        ("Synthesis and qualification", "Integrate viewpoints, explain methodological differences and qualify a conclusion.", [3]),
        ("Complex prose and register", "Interpret implicit relations and explain stylistic effects in varied texts.", []),
        ("Extended multi-speaker listening", "Track stance changes, qualifications and implicit assumptions across speakers.", []),
        ("Multi-source written argument", "Produce a well-structured synthesis that handles counterarguments accurately.", []),
        ("Fluent speaking and prosody", "Reformulate flexibly and use emphasis/rhythm to support a nuanced argument.", []),
        ("C1 cumulative review", "Integrate complex sources and defend a precise, appropriately qualified position.", []),
    ],
    "C2": [
        ("Rhetoric and implied conditions", "Analyse what a promise presupposes without confusing rhetoric with evidence.", [1]),
        ("Concession and logical scope", "Concede the force of an objection while delimiting what it establishes.", [2]),
        ("Pragmatics, irony and audience", "Adapt commitment, presupposition and irony to two different audiences.", [3]),
        ("Dense and varied texts", "Interpret allusion, ambiguity and fine stylistic distinctions across genres.", []),
        ("Nuanced spoken comprehension", "Explain implicit attitudes, humour and shifts of register in extended speech.", []),
        ("Sophisticated spontaneous interaction", "Handle challenge and ambiguity while maintaining precision and flexibility.", []),
        ("Critical synthesis and mediation", "Reconstruct a complex argument and reformulate it without losing nuance.", []),
        ("C2 cumulative review", "Integrate demanding sources and produce precise extended speech and writing for a defined audience.", []),
    ],
}


def build():
    stages=[]; previous=None
    for code, rows in CURRICULUM.items():
        modules=[]
        for number,(title,outcome,refs) in enumerate(rows,1):
            identity=f"{code.lower()}-{number:02}"
            slugs=[]
            for ref in refs:
                if isinstance(ref,str):slugs.append(ref)
                else:slugs.extend(f"m10-assessments-{code.lower()}-0.2.1-module-{ref}-{skill}" for skill in ('grammar','vocabulary','reading','writing'))
            if code=='A1':
                extra={2:['tell-the-time','days-and-dates','write-a-meeting-message'],
                       3:['describe-clothes','negate-a-quantity'],5:['a-morning-routine'],6:['ask-a-price'],
                       7:['locate-a-place','go-to-a-place'],8:['an-appointment-request','ask-someone-to-repeat'],9:['a-day-and-a-request']}
                slugs.extend(f'm10-assessments-a1-0.3.2-{key}' for key in extra.get(number,[]))
            modules.append(dict(id=identity,title=title,objective=outcome,outcomes=[outcome],
                prerequisites=[previous] if previous else [],lesson_slugs=slugs,
                required_skills=['vocabulary','grammar','reading','listening','writing','speaking'],
                revision='Retrieve earlier vocabulary, correct saved mistakes and reuse the language in a new situation.',
                assessment='Use task evidence across skills; completion alone does not establish a CEFR level.',
                coverage='partial' if refs else 'pending'))
            previous=identity
        # Source-only scenario releases remain invisible until separately imported.
        scenario_versions={'A0':'0.4.7','A1':'0.4.1','A2':'0.4.2','B1':'0.4.3','B2':'0.4.4','C1':'0.4.5','C2':'0.4.6'}
        target={'A0':2,'A1':6,'A2':4,'B1':4,'B2':4,'C1':4,'C2':4}[code]-1
        stored='a1' if code=='A0' else code.lower()
        modules[target]['lesson_slugs'].extend(f'm10-assessments-{stored}-{scenario_versions[code]}-{key}'
            for key in ('interpret-scenario','transfer-and-review'))
        modules[target]['coverage']='partial'
        depth={'A0':(3,'0.6.0'),'A1':(8,'0.6.1'),'B2':(5,'0.6.2'),'C1':(6,'0.6.3'),'C2':(7,'0.6.4')}
        if code in depth:
            number,version=depth[code]
            modules[number-1]['lesson_slugs'].extend(f'm10-assessments-{stored}-{version}-{key}'
                for key in ('input-1','input-2','integrate-and-transfer'))
            modules[number-1]['coverage']='partial'
        missing={'A2':[5,6,7,8],'B1':[5,6,7,8],'B2':[6,7,8],'C1':[5,7,8],'C2':[5,6,8]}
        for number in missing.get(code,[]):
            modules[number-1]['lesson_slugs'].extend(f'm10-assessments-{stored}-0.7.{number}-{key}'
                for key in ('read-and-notice','listen-and-integrate','transfer-and-assess'))
            modules[number-1]['coverage']='partial'
        bridges={'A0':{1:'letters-and-name-writing'},'A1':{1:'greet-introduce-close',3:'first-sentences-writing',4:'people-and-possessions-writing',5:'routine-writing-and-repair'}}
        for number,key in bridges.get(code,{}).items():
            version='0.9.0' if code=='A0' else '0.9.1'
            modules[number-1]['lesson_slugs'].append(f'm10-assessments-a1-{version}-{key}')
        stages.append(dict(code=code,official_cefr=code!='A0',modules=modules,
            introduction='Absolute beginner preparation; not an official CEFR level.' if code=='A0' else 'Progressive practice target; independent calibration pending.'))
    return dict(version='1.4.0',stages=stages,certification=False)


if __name__=='__main__':
    path=Path(__file__).resolve().parents[1]/'content/learning-path.json'
    path.write_text(json.dumps(build(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Learning path map written: A0 through C2; pending coverage remains explicit.')
