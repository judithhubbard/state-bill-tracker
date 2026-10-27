"""The stages every state's bills are sorted into, numbered 0-6 (6 = vetoed)."""


STAGE_LABEL = ["In committee", "On the floor", "Passed one house", "Passed both houses",
               "Delivered to governor", "Signed into law", "Vetoed"]


def rank(stage):
    # Vetoed sits after delivered but before signed when choosing the furthest version.
    return {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 6: 5, 5: 6}[stage]
