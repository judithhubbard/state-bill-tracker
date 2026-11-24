"""What the bill does first, for summaries that open with the law as it stands.

Wisconsin's and Colorado's analysts write what current law says, then what the bill changes ("Under current law, ...
This bill ..."), as California's, Nevada's, Missouri's and Louisiana's do; those states' converters already put the
bill's part first (states/ca/texts.py, states/nv/convert.py's `digest_text()`, states/mo/convert.py,
states/la/convert.py). `lead_first()` does the same for a list of paragraphs, without changing a word: the first
sentence that says what the bill does moves to the top with the rest of its paragraph, and everything before it
follows, in its own order. Nothing moves when the text doesn't open with background, or when no sentence says what
the bill does.

Sentences are split as states/billtext_lead.py's `sentences()` splits them (not after "Sec.", "Minn. Stat.", "H.B.",
"O.C.G.A.", a list's "2."), and only once: just before the sentence that moves, so a numbered list is never cut.
"""
import re

from states.billtext_lead import sentences

# The first sentence describes the law as it stands.
BACKGROUND = re.compile(
    r"^(?:Under (?:current|existing|present|prior|federal|state) (?:law|statutes?)|(?:Current|Existing|Present|Prior) "
    r"(?:law|statutes?)\b|Currently\b|Under current\b|Under the current\b|Current (?:federal|state) law\b)")

def does(*names):
    """A sentence that says what the bill does, for the words a state's analysts call it by: "This bill ...", "The act
    ...", "Under the bill, ...", "Beginning with pupils graduating in 2028, this bill requires ..."."""
    n = "|".join(sorted(names, key=len, reverse=True))
    return re.compile(rf"^(?:(?:This|The) (?:{n})\b|Under (?:this|the) (?:{n})\b|"
                      rf"[A-Z][^.;:]{{0,100}}?, (?:this|the) (?:{n}) (?!as\b|is\b)[a-z]+s\b)")


# Wisconsin's LRB says "bill" (and "substitute amendment", "proposal"); "the act" there is an earlier law. Colorado's
# staff say "the act" for a bill that became law.
DOES = does("bill", "act", "resolution", "joint resolution", "concurrent resolution", "substitute amendment",
            "proposed constitutional amendment", "constitutional amendment", "measure")

# A list item on a line of its own: "1. ...", "a) ...", "(b) ...", "• ...".
ITEM = re.compile(r"^(?:\(?\d{1,2}[.)]|\(?[a-z][.)]|[•\-–])\s")

# Words after "this"/"that" that name the bill or the law, not something the background described.
OWN = {"bill", "act", "state", "section", "sections", "chapter", "subchapter", "subsection", "paragraph", "resolution",
       "substitute", "amendment", "proposal", "measure", "year", "time", "date"}


def refers_back(sentence, before):
    """Whether the bill's sentence leans on the background before it ("This bill eliminates that prohibition.", "The bill
    increases that annual cap to ...", "provides the same benefit", "instead provides"): read first, it wouldn't make
    sense, so those texts keep their order."""
    s = sentence[:160]
    if re.search(r"\b(?:the same|instead|also|above|aforementioned|the existing|similar|both|these|those|such(?! as\b)|accordingly|"
                 r"therefore|thus|consequently|however)\b", s, re.I):
        return True
    # "This bill extends the exception to ...", "eliminates the preemption so that ...": a rule named with "the" and
    # nothing after it saying which.
    if re.search(r"\bthat (?:[a-z]+ )?(?:exceptions?|exemptions?|requirements?|prohibitions?|preemption|limits?|caps?|"
                 r"provisions?|process|procedures?|list|deadline|restrictions?|ban|thresholds?|period|definition|rule|"
                 r"program|authority|duty|right|penalty|fee|amount|rate|plan|purpose)\b", s):
        return True
    if re.search(r"\bthe (?:[a-z]+ )?(?:exceptions?|exemptions?|requirements?|prohibitions?|preemption|limits?|cap|caps|"
                 r"provisions?|process|procedures?|list|deadline|restrictions?|ban|thresholds?|period|program|board|"
                 r"council|commission|fund|penalty|penalties|notice|office|grants?|credit|plan|report|offense|"
                 r"violations?|definition|account|task force|committee|registry|system)\b"
                 r"(?! (?:of|for|on|under|that|which|in|against|related|relating|regarding|imposed|established)\b)", s):
        return True
    # "This bill expands this definition ...": "this" before anything but the bill, the state or the like.
    for m in re.finditer(r"\bthis ([\w-]+)", s):
        if m.group(1) not in OWN:
            return True
    low = before.lower()
    # "that" before an article or a pronoun is a conjunction ("provides that a complainant ..."), not "that prohibition":
    # it counts when the word after it (or the one after that) was in the background.
    for m in re.finditer(r"\bthat (?!(?:a|an|the|any|no|each|all|every|if|in|for|to|it|he|she|they|"
                         r"person|individual|is|are|was|were|has|have|may|must|would|will|can|shall)\b)([a-z][\w-]+)(?: ([a-z][\w-]+))?", s):
        for w in m.groups():
            if w and len(w) > 3 and w.lower() not in OWN and w.lower()[:4] in low:
                return True
    return False


def lead_first(paras, bill=DOES, background=BACKGROUND):
    """The paragraphs (a list of strings) with what the bill does first. Returns the list unchanged, or a new list with
    the same sentences: [the bill's sentence and the rest of its paragraph] + every paragraph before it + the part of
    its own paragraph before it (a paragraph of its own) + the paragraphs after it."""
    paras = [p for p in paras if p and p.strip()]
    if not paras or not background.match(paras[0].strip()):
        return paras
    for i, p in enumerate(paras):
        ss = sentences(p.strip())
        j = next((k for k, s in enumerate(ss) if bill.match(s)), None)
        if j is None:
            continue
        if i == 0 and j == 0:
            return paras
        if refers_back(ss[j], " ".join(paras[:i] + ss[:j])):
            return paras
        rest, note = ss[j:], []
        if i == len(paras) - 1 and len(rest) > 1 and re.match(r"\(Note:", rest[-1]):
            # Colorado's "(Note: This summary applies to this bill as enacted.)" stays last.
            rest, note = rest[:-1], rest[-1:]
        head, tail = " ".join(ss[:j]), " ".join(rest)
        if head.endswith(":"):
            return paras
        # A list the bill's sentence introduces ("... does all of the following:" then "1. ...") moves with it.
        k = i + 1
        if tail.endswith(":"):
            while k < len(paras) and ITEM.match(paras[k].strip()):
                k += 1
            if k == i + 1 and k < len(paras):
                return paras  # a list whose lines aren't numbered (Colorado's): where it ends isn't sure
        out = [tail] + paras[i + 1:k] + paras[:i] + ([head] if head else []) + paras[k:]
        if note:
            out[-1] += " " + note[0]
        return out
    return paras


def opens_with_background(text, background=BACKGROUND):
    """Whether a text's first line is the law as it stands (test/data_check.py's LOOK)."""
    first = (text or "").strip().split("\n")[0]
    return bool(background.match(first))


# Words a subject label is said with that name no subject ("Provisions relating to ...", "Appropriations bill").
_STOP = {"of", "the", "and", "for", "in", "on", "to", "a", "an", "or", "by", "with", "at", "from", "as", "its", "their",
         "certain", "various", "bill", "bills", "act", "provisions", "provision", "relating", "related", "regarding",
         "concerning", "matters", "issues", "s"}


def words(t):
    """A text's words in order, lowercase, without the words above and a plural's "s" ("codes" -> "code")."""
    return [re.sub(r"(?<=[a-z]{3})(?:es|s)$", "", w) for w in re.findall(r"[a-z0-9]+", (t or "").lower()) if w not in _STOP]


def repeats(label, *shown):
    """Whether a subject label ("Gender transition procedures", "Relating to building codes") says nothing the page
    doesn't already show: its words, in order, are words of the title or the text shown with it ("Modifies provisions
    relating to gender transition procedures"). Words found apart don't count ("Relating to suicide prevention" for
    "Establishes a Prevent Suicide Hawai‘i Working Group"), nor another form of a word ("homelessness", "Homeless")."""
    w = words(label)
    if not w:
        return False
    for t in shown:
        have = words(t)
        if any(have[i:i + len(w)] == w for i in range(len(have) - len(w) + 1)):
            return True
    return False
