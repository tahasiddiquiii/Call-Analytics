from callanalytics.parser import parse_file, parse_text
from tests.conftest import DATA, FIXTURES


def test_all_provided_calls_parse_cleanly():
    for path in sorted(DATA.glob("*.txt")):
        t = parse_file(path)
        assert t.call_id == path.stem
        assert t.turns, path
        assert t.unparsed_lines == 0, path
        assert {x.speaker for x in t.turns} <= {"System", "Agent", "Customer"}


def test_brand_extraction_drops_department_words():
    assert parse_file(DATA / "call_010.txt").brand == "Nimbus Home Networks"
    assert parse_file(DATA / "call_002.txt").brand == "Skyline Broadband"
    assert parse_file(DATA / "call_004.txt").brand is None  # test call has no brand


def test_messy_file_keeps_text_and_counts_bad_lines():
    t = parse_file(FIXTURES / "edge" / "messy.txt")
    assert t.brand == "Acme Water"
    assert t.turns[2].text == "My bill is wrong and it is far too high."
    assert t.unparsed_lines == 2  # wrapped line + unknown 'Supervisor:' speaker
    assert t.turns[3].speaker == "Unknown"  # not credited to the customer
    assert t.warnings


def test_empty_file_has_no_turns():
    assert parse_file(FIXTURES / "edge" / "empty.txt").turns == []


def test_invalid_utf8_is_tolerated_and_flagged():
    t = parse_file(FIXTURES / "edge" / "latin1.txt")
    assert t.decode_errors and len(t.turns) == 2


def test_speaker_labels_are_case_insensitive():
    t = parse_text("x", "agent: hi\nCUSTOMER : hello")
    assert [x.speaker for x in t.turns] == ["Agent", "Customer"]
    assert t.render() == "[1] Agent: hi\n[2] Customer: hello"
