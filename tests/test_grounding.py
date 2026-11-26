from callanalytics.grounding import compact, quote_in_transcript, reference_in_transcript


def test_spoken_ids_match_written_ids():
    said = ["The reference number is R-F-two-two-zero-six-eight."]
    assert reference_in_transcript("RF-22068", said)
    assert reference_in_transcript("rf 22068", said)
    assert not reference_in_transcript("RF-22069", said)


def test_ids_with_dash_words_and_fillers():
    assert reference_in_transcript("CLM-291-446", ["It's C L M, dash, two nine one, dash, four four six."])
    assert reference_in_transcript("BC-774192", ["It's B C, uh, B-C-seven-seven-four-one-nine-two."])
    assert reference_in_transcript("CL-9031", ["claim C-L-nine-oh-three-one."])
    assert reference_in_transcript("TK-44180", ["The reference is T-K, four four one, eight zero."])


def test_double_and_triple():
    assert compact("five double zero one four") == "50014"
    assert compact("triple seven") == "777"


def test_too_short_ids_are_never_verified():
    assert not reference_in_transcript("A1", ["A1 A1 A1"])


def test_quotes_must_be_word_for_word_but_ignore_punctuation_and_case():
    turns = ["Fine. Thanks, I guess. Don't make me call back."]
    assert quote_in_transcript("thanks I guess", turns)
    assert quote_in_transcript("Don't make me call back", turns)
    assert not quote_in_transcript("Thanks, I am happy", turns)


def test_canonical_reference_format():
    from callanalytics.grounding import canonical_reference

    assert canonical_reference("R-F-22068") == "RF-22068"
    assert canonical_reference("e s c 7812") == "ESC-7812"
    assert canonical_reference("CLM-291-446") == "CLM-291446"
    assert canonical_reference("E S C seven eight one two") == "ESC-7812"  # v2 stored "ESCSEVENEIGHTONETWO"


def test_spoken_ids_are_extracted_by_code_only_near_case_words():
    from callanalytics.parser import parse_text
    from callanalytics.references import extract_references

    t = parse_text("x", "\n".join([
        "Agent: Can I have your claim number?",
        "Customer: It's C L M, dash, two nine one, dash, four four six.",
        "Agent: The escalation reference is E-S-C, seven eight one two.",
        "Customer: My number is five five five, oh one two nine.",  # phone: no letters, never an ID
        "Agent: It says N, B, dash, four, one, nine on the router.",  # no case word nearby
        "Customer: It's B C, uh, B-C-seven-seven-four-one-nine-two, the order.",
        "Agent: I can refund a 100 dollars.",  # article 'a' is not an ID prefix
    ]))
    assert extract_references(t.turns) == [("claim", "CLM-291446"), ("escalation", "ESC-7812"), ("order", "BC-774192")]
