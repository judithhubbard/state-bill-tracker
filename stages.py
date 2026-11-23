"""The stages every state's bills are sorted into, numbered 0-6 (6 = vetoed), and how a law got there."""
import re


STAGE_LABEL = ["In committee", "On the floor", "Passed one house", "Passed both houses",
               "Delivered to governor", "Became law", "Vetoed"]


def rank(stage):
    # Vetoed sits after delivered but before signed when choosing the furthest version.
    return {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 6: 5, 5: 6}[stage]


# How a law got there, as its history says: tracker.html's NO_SIGNATURE, SIGNATURE, ENROLL_SIGNED and hasSignature() (keep
# them alike; test/wording_check.js compares them on every state's laws). build_data.py's governor_record() reads them.
# A law the governor neither signed nor vetoed in time (or, in some states, returned unsigned).
NO_SIGNATURE = re.compile(r"without (?:the |my )?(?:governor'?s |president'?s |mayor'?s )?signature|w/o (?:the )?(?:governor'?s? )?sign|w/out governor", re.I)
# A line saying the governor (or the President) signed it; not the presiding officers' signatures on the enrolled bill.
SIGNATURE = re.compile(r"\bsigned\b(?! by the (?:speaker|president of the senate|president pro|senate president|lieutenant|presiding|chief clerk|secretary))|approved by (?:the )?governor|governor approved", re.I)
ENROLL_SIGNED = re.compile(r"signed by the (?:speaker|president of the senate|president pro|senate president|lieutenant|presiding)|presiding officers?'? signature|\(enrolled\)", re.I)


def _lines(rec):
    return (a[1] or "" for v in rec["vers"] for a in v["actions"])


def unsigned(rec):
    """The history says the law came without the signature."""
    return any(NO_SIGNATURE.search(t) for t in _lines(rec))


def has_signature(rec):
    """The history has the governor's (or President's) signature."""
    return any(SIGNATURE.search(t) and not ENROLL_SIGNED.search(t) for t in _lines(rec))
