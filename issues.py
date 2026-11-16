"""National issues: which bills, in every state, are about the same subject (notes/issues-draft.md; the owner's answers
2026-11-15). A bill is about an issue when its title, summary or "What it does" text matches one of the issue's rules.

A rule is a list of patterns that must all appear (the first is the anchor; the others within WINDOW characters of it,
so a long text doesn't match on words pages apart), and a list it must not have in that window. Patterns are regular
expressions matched without regard to case, except those starting "(?-i)"; one starting "!" is an exclusion for that
rule alone. Bills for one city or county (narrow
"place") and placeholder bills (shell) are left out. `filters` are the subsets an issue's page offers (AI: deepfakes,
chatbots ...); a bill can be in several.

A match in the title or summary counts; so does one in a short "What it does" (under SHORT characters); a longer one
needs two mentions (budget and omnibus bills mention a subject once in passing; checked 2026-11-15).

`issues_of(head, body)` gives the issue ids a bill matches (head: title and summary; body: "What it does");
`filters_of(issue, text)` its filters.
"""
import re

WINDOW = 400
# The menu's groups, in order (the owner's choice 2026-11-15); each issue is in one.
GROUPS = ["Technology", "Schools", "Health", "Housing and taxes", "Work and the economy", "Environment and energy",
          "Rights and public safety", "Elections"]
SHORT = 1500

ISSUES = [
    {"id": "datacenters", "group": "Technology", "name": "Data centers",
     "rules": [[r"\bdata ?cent(?:er|re)s?\b"], [r"\bhyperscale"], [r"\bhigh[- ]performance computing\b"],
               [r"\b(?:large|high)[- ]loads?\b", r"!\b(?:vehicles?|trailers?|trucks?|highways?|lanes?)\b"],
               [r"\b(?:large|high)[- ](?:energy[- ]use|energy[- ]demand|energy|use|load[- ]factor)(?: electric)? (?:facilit\w+|customers?|users?|consumers?)\b"]],
     "none": [r"\bstate data cent(?:er|re)", r"\bconsolidat\w*\b.{0,60}\bdata cent", r"\bdata cent(?:er|re)s? (?:services|consolidation)\b"]},
    {"id": "pfas", "group": "Environment and energy", "name": "PFAS (“forever chemicals”)",
     "rules": [[r"\bPFAS\b"], [r"perfluoro"], [r"polyfluoro"], [r"perfluorinated"], [r"\bforever chemicals?\b"],
               [r"\bPFOA\b"], [r"\bPFOS\b"], [r"\bfire[- ]?fighting foams?\b"], [r"(?-i)\bAFFF\b"],
               [r"\baqueous film[- ]forming foam"],
               [r"\b(?:turnout gear|firefighters?'? (?:personal )?protective (?:equipment|clothing))\b", r"\b(?:chemicals?|toxic|substances?)\b"]]},
    {"id": "ai", "group": "Technology", "name": "Artificial intelligence",
     "rules": [[r"\bartificial intelligence\b"], [r"\bgenerative (?:AI|artificial)"], [r"\bAI[- ]generated\b"],
               [r"(?-i)\bAI\b"], [r"\bdeep ?fakes?\b"], [r"\bsynthetic media\b"],
               [r"\bdigitally (?:altered|fabricated|manipulated|created)\b", r"\b(?:image|video|audio|likeness|depiction|recording)s?\b"],
               [r"\bdigital (?:replicas?|likeness(?:es)?)\b"], [r"\bsynthetic (?:sexual |intimate |explicit )?(?:images?|imagery|videos?)\b"],
               [r"\bpricing algorithms?\b"], [r"\bchat ?bots?\b"], [r"\bautomated decision(?:[- ]making)? (?:tools?|systems?)\b"],
               [r"\balgorithmic discrimination\b"]],
     "none": [r"\binsemination\b"],
     "filters": {"Deepfakes and elections": [r"\bdeep ?fake", r"\bsynthetic media\b", r"\bdigitally (?:altered|fabricated|manipulated|created)\b", r"\belection"],
                 "Chatbots": [r"\bchat ?bots?\b", r"\bcompanion\b"],
                 "Hiring, insurance and decisions": [r"\bautomated decision", r"\balgorithmic discrimination\b", r"\bemploy", r"\bhiring\b", r"\binsur"],
                 "Government use": [r"\bstate agenc", r"\bgovernmental? (?:entit|agenc|bod|unit)", r"\bpublic (?:bod|entit|agenc)"]}},
    {"id": "kidsonline", "group": "Technology", "name": "Children online and social media",
     "filters": {"Age checks for adult websites": [r"\bpornograph", r"\bharmful (?:to minors|material)\b", r"\badult[- ](?:only )?(?:websites?|content|material)\b", r"\bsexual material\b"],
                 "Social media": [r"\bsocial (?:media|networking)\b"], "App stores": [r"\bapp stores?\b"],
                 "Design and privacy codes": [r"\bage[- ]appropriate design\b", r"\bkids code\b", r"\b(?:data|privacy)\b"]},
     "rules": [[r"\bsocial (?:media|networking)\b", r"\b(?:minors?|child|children|teens?|teenagers?|under (?:the age of )?1[3-8]|age of 1[3-8]|parents?|youth)\b"],
               [r"\bage verification\b", r"\b(?:websites?|online|internet|apps?|applications?|platforms?)\b",
                r"!\b(?:alcohol|tobacco|vap(?:e|or|ing)|nicotine|firearms?|lottery|cannabis|marijuana|liquor|wager\w*|gaming|gambling|nitrite)\b"],
               [r"\b(?:online (?:services?|platforms?|products?)|digital services?)\b", r"\b(?:minors?|child|children|teens?|kids)\b"],
               [r"\bharmful (?:to minors|material)\b", r"\b(?:online|internet|websites?|digital|apps?)\b"],
               [r"\bage[- ]appropriate design\b"], [r"\bapp stores?\b", r"\b(?:minors?|age|parent)"]]},
    {"id": "phones", "group": "Schools", "name": "Phones in schools",
     "rules": [[r"\b(?:cell(?:ular)? ?(?:tele)?phones?|smart ?phones?|wireless (?:communication|telecommunication)s? devices?|personal (?:electronic|communication|telecommunications?) devices?|(?:mobile|wireless|portable electronic|internet[- ]enabled|electronic|electronic telecommunications?) devices?|phone[- ]free)\b",
                r"\b(?:schools?|students?|classrooms?|instructional (?:time|day))\b",
                r"\b(?:use|uses|using|possess\w*|prohibit\w*|ban|bans|banned|polic(?:y|ies)|restrict\w*|free|limit\w*|access)\b",
                r"!\b(?:recycl\w*|e-?waste|audits?)\b"]],
     "none": [r"\b(?:stopped|passing a) school bus", r"\bdistrict[- ]owned\b", r"\bwhile driving\b", r"\boperat\w* a (?:motor )?vehicle\b", r"\bbus drivers?\b", r"\bschool zones?\b"]},
    {"id": "housing", "group": "Housing and taxes", "name": "Housing supply and zoning",
     "rules": [[r"\baccessory dwelling"], [r"(?-i)\bADUs?\b"], [r"\bmissing[- ]middle\b"], [r"\bsingle[- ]family zon"],
               [r"\b(?:duplex|triplex|fourplex|quadplex)(?:es)?\b"], [r"\bminimum lot sizes?\b"],
               [r"\bparking (?:minimums?|requirements?|mandates?)\b", r"\bhous"], [r"\bby[- ]right\b", r"\bhous"],
               [r"\bhousing (?:production|supply)\b"], [r"\bhousing elements?\b"], [r"\bmulti-?family\b", r"\bzon(?:e|ed|ing)\b"],
               [r"\bdensity\b", r"\bhousing\b", r"\bzon(?:e|ed|ing)\b"], [r"\bstarter homes?\b"], [r"\bmanufactured hous", r"\bzon"]]},
    {"id": "minwage", "group": "Work and the economy", "name": "Minimum wage",
     # Only bills that set or change a minimum wage (the owner's decision 2026-11-15): not ones paying for its cost or
     # setting other pay by it.
     "rules": [[r"\bminimum (?:hourly )?wages?\W+(?:\w+\W+){0,6}?(?:increas\w*|rais\w*|establish\w*|eliminat\w*|repeal\w*|"
                r"exempt\w*|modif\w*|chang\w*|adjust\w*|index\w*|phas\w*|decreas\w*|reduc\w*|cost[- ]of[- ]living|per hour|"
                r"preempt\w*|ordinances?|rates?|act|law|amendments?|\$\d)"],
               [r"\b(?:increas\w*|rais\w*|establish\w*|sets?|eliminat\w*|repeal\w*|exempt\w*|modif\w*|chang\w*|adjust\w*|"
                r"index\w*|decreas\w*|reduc\w*|local|state|preempt\w*|regulat\w*|tipped)\W+(?:\w+\W+){0,6}?minimum (?:hourly )?wages?\b"],
               [r"\bsubminimum wages?\b"], [r"\btipped (?:minimum )?(?:wages?|employees?|workers?)\b"],
               [r"\btip credits?\b"], [r"\btraining wages?\b"]],
     "none": [r"\btimes the (?:state |federal |applicable )?minimum (?:hourly )?wage\b", r"\bjur(?:y|ors?)\b",
              r"\b(?:state funds?|operating costs?|costs? associated|reimburse\w*|tax credits?|grants?|grant programs?|"
              r"income tax|sales and use tax|sales tax|taxable income)\b"]},
    {"id": "repair", "group": "Technology", "name": "Right to repair",
     "rules": [[r"\bright[- ]to[- ]repair\b"], [r"\bdevices? repair\b"], [r"\bfair repair\b"], [r"\bdigital electronic (?:equipment|products?)\b", r"\brepair"],
               [r"\bindependent repair\b", r"\b(?:parts|tools|documentation|diagnostic)"],
               [r"\brepair", r"\b(?:powered wheelchairs?|wheelchairs?|agricultural equipment|farm equipment)\b"]],
     "none": [r"\bbody shops?\b", r"\bmotor vehicle repair\b", r"\bauto(?:mobile|motive)? repair\b"]},
    {"id": "betting", "group": "Work and the economy", "name": "Sports betting and online gambling",
     "rules": [[r"\bsports (?:wagering|betting|wagers?|pools?|gaming)\b"], [r"\bsportsbooks?\b"], [r"\bi-?gaming\b"],
               [r"\binternet (?:gambling|casino)"], [r"\b(?:internet|online) gaming\b", r"\b(?:wager\w*|casinos?|gambl\w*|bets?|betting)\b"],
               [r"\bonline (?:casino|gambling|poker|lottery|sports)"],
               [r"\bsweepstakes casino"], [r"\bsweepstakes\b", r"\bgam(?:ing|bling|es)\b"],
               [r"\bfantasy (?:sports|contests?)\b"], [r"\bprediction markets?\b"]],
     "none": [r"\braffles?\b", r"\bbingo\b"]},
    {"id": "drugcosts", "group": "Health", "name": "Prescription drug costs",
     "rules": [[r"\binsulin\b", r"\b(?:costs?|prices?|pricing|co-?pay(?:ment)?s?|cost[- ]sharing|caps?|capped|out-of-pocket|affordab)"],
               [r"\bprescription drug affordability\b"], [r"\bpharmacy benefits? managers?\b"], [r"(?-i)\bPBMs?\b"],
               [r"\bdrug pric(?:e|es|ing)\b"], [r"\b(?:prescription )?drug (?:costs?|affordability)\b"],
               [r"\bprescription drugs?\b", r"\b(?:cost[- ]sharing|co-?pay(?:ment)?s?|out-of-pocket)\b"], [r"\b340B\b"]]},
]


def _compile(p):
    if p.startswith("(?-i)"):
        return re.compile(p[5:])
    return re.compile(p, re.I)


for _issue in ISSUES:
    _issue["_rules"] = [([_compile(p) for p in rule if not p.startswith("!")],
                         [_compile(p[1:]) for p in rule if p.startswith("!")]) for rule in _issue["rules"]]
    _issue["_none"] = [_compile(p) for p in _issue.get("none", [])]
    _issue["_filters"] = {k: [_compile(p) for p in v] for k, v in _issue.get("filters", {}).items()}
BY_ID = {i["id"]: i for i in ISSUES}


def _hit(issue, text):
    """The first window of text where one of the issue's rules matches and no exclusion appears, or None."""
    for need, avoid in issue["_rules"]:
        for m in need[0].finditer(text):
            a, b = max(0, m.start() - WINDOW), m.end() + WINDOW
            win = text[a:b]
            if all(p.search(win) for p in need[1:]) and not any(p.search(win) for p in issue["_none"] + avoid):
                return win
    return None


def _hits(issue, text, enough):
    """How many mentions of the issue (anchor matches whose window passes) the text has, counting up to `enough`."""
    found = set()
    for need, avoid in issue["_rules"]:
        for m in need[0].finditer(text):
            win = text[max(0, m.start() - WINDOW):m.end() + WINDOW]
            if all(p.search(win) for p in need[1:]) and not any(p.search(win) for p in issue["_none"] + avoid):
                found.add(m.start())
                if len(found) >= enough:
                    return len(found)
    return len(found)


def issues_of(head, body=""):
    """The ids of the issues a bill matches: in its title and summary (head), or twice in its "What it does" (body)."""
    need = 1 if len(body) < SHORT else 2
    return [i["id"] for i in ISSUES if _hit(i, head) or (body and _hits(i, body, need) >= need)]


def snippet(issue_id, text):
    """The window that matched, for reading matches over."""
    return _hit(BY_ID[issue_id], text)


def filters_of(issue_id, text):
    return [k for k, ps in BY_ID[issue_id]["_filters"].items() if any(p.search(text) for p in ps)]


def excerpt(issue_id, head, body="", limit=220):
    """The sentence (or clause between semicolons) where the issue matched, for showing why a bill with a bare title
    ("Wages") is on the issue: from the summary if it matched there, else from "What it does". A leading statute
    reference ("Amend KRS 337.275 to raise ...") is dropped. "" when nothing matched."""
    issue = BY_ID[issue_id]
    for text in (head, body):
        if not text:
            continue
        for need, avoid in issue["_rules"]:
            for m in need[0].finditer(text):
                win = text[max(0, m.start() - WINDOW):m.end() + WINDOW]
                if not all(p.search(win) for p in need[1:]) or any(p.search(win) for p in issue["_none"] + avoid):
                    continue
                a = max(text.rfind(". ", 0, m.start()), text.rfind("; ", 0, m.start()))
                b = min([x for x in (text.find(". ", m.end()), text.find("; ", m.end())) if x >= 0] or [len(text)])
                s = re.sub(r"\s+", " ", text[a + 2 if a >= 0 else 0:b]).strip()
                s = re.sub(r"^(?:[Aa]mends?|[Cc]reates?|[Rr]epeals?)(?: (?:a )?new sections? of)? [A-Z]{2,5} (?:Chapter )?[\d.,A-Z\s-]+?(?:and [\d.]+ )?to ", "", s)
                if len(s) > limit:
                    s = s[:limit].rsplit(" ", 1)[0] + " …"
                return s[:1].upper() + s[1:]
    return ""
