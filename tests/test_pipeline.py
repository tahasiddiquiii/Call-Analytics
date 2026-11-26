import json
import shutil

import pytest

from callanalytics import __main__ as cli
from callanalytics.config import PROMPTS_DIR, Settings
from callanalytics.pipeline import Prompts, analyse_call, run
from callanalytics.schema import CallRecord, OutputFile
from tests.conftest import DATA, FIXTURES, valid_answer

SETTINGS = Settings()
PROMPTS = Prompts.load()


def test_valid_answer_becomes_ok_record(fake):
    rec = analyse_call(DATA / "call_005.txt", fake(valid_answer()), PROMPTS, SETTINGS)
    assert rec.status == "ok" and rec.call_id == "call_005"
    assert rec.client_brand == "Northwave Mobile"
    assert rec.references[0].verified  # RF-22068 is said in call_005
    assert rec.sentiment.trajectory == "improved"


def test_invented_reference_and_quote_trigger_review(fake):
    answer = valid_answer(
        references=[{"type": "refund", "value": "RF-99999"}],
        evidence=[{"supports": "outcome", "turn": 3, "quote": "I approve everything forever"}],
    )
    rec = analyse_call(DATA / "call_005.txt", fake(answer), PROMPTS, SETTINGS)
    assert rec.needs_review
    assert not rec.references[0].verified and not rec.evidence[0].verified
    assert any("RF-99999" in r for r in rec.review_reasons)


def test_invalid_json_is_repaired_on_second_attempt(fake):
    client = fake("{not json", valid_answer())
    rec = analyse_call(DATA / "call_005.txt", client, PROMPTS, SETTINGS)
    assert rec.status == "ok" and rec.quality.attempts == 2
    assert "could not be used" in client.calls[1][-1]["content"]  # repair prompt was sent


def test_wrong_enum_value_fails_validation_then_fails_cleanly(fake):
    bad = valid_answer(outcome={"status": "kind_of_done", "detail": "x"})
    rec = analyse_call(DATA / "call_005.txt", fake(bad), PROMPTS, SETTINGS)
    assert rec.status == "failed" and rec.needs_review
    assert rec.summary is None and rec.action_items == []
    assert "schema" in rec.error


def test_model_timeout_gives_failed_record(fake, model_error):
    rec = analyse_call(DATA / "call_005.txt", fake(model_error), PROMPTS, SETTINGS)
    assert rec.status == "failed" and "600s" in rec.error


def test_contradictions_are_flagged(fake):
    answer = valid_answer(call_type="test_call")  # but outcome says resolved
    rec = analyse_call(DATA / "call_004.txt", fake(answer), PROMPTS, SETTINGS)
    assert rec.needs_review
    assert any("call_type is test_call" in r for r in rec.review_reasons)
    assert rec.supervisor_priority == "low"


def test_phone_numbers_in_free_text_are_flagged(fake):
    answer = valid_answer(summary="Customer on 555 0194 4471 called.")
    rec = analyse_call(DATA / "call_005.txt", fake(answer), PROMPTS, SETTINGS)
    assert any("phone or card" in r for r in rec.review_reasons)


def test_compliance_insight_sets_flag_and_high_priority(fake):
    answer = valid_answer(insights=[{"category": "compliance_risk", "text": "Agent guaranteed approval.",
                                     "quote": "I guarantee it, no deductible either"}])
    rec = analyse_call(DATA / "call_006.txt", fake(answer), PROMPTS, SETTINGS)
    assert rec.flags.compliance_risk and rec.supervisor_priority == "high"


def test_run_never_stops_on_bad_files_and_output_is_consistent(tmp_path, fake, model_error):
    folder = tmp_path / "calls"
    folder.mkdir()
    shutil.copy(FIXTURES / "edge" / "empty.txt", folder / "call_a.txt")
    shutil.copy(FIXTURES / "edge" / "messy.txt", folder / "call_b.txt")
    shutil.copy(DATA / "call_005.txt", folder / "call_c.txt")
    out = tmp_path / "out" / "records.json"
    client = fake(valid_answer(), model_error, model_error)  # b ok, c fails twice
    run(folder, out, client, SETTINGS, runtime="test")

    data = json.loads(out.read_text())
    OutputFile.model_validate(data)  # whole file matches the published schema
    recs = {r["call_id"]: r for r in data["records"]}
    assert [r["call_id"] for r in data["records"]] == ["call_a", "call_b", "call_c"]
    assert recs["call_a"]["status"] == "failed"  # empty file
    assert recs["call_b"]["status"] == "ok" and recs["call_b"]["needs_review"]  # messy lines flagged
    assert recs["call_c"]["status"] == "failed"
    keys = {tuple(r.keys()) for r in data["records"]}
    assert len(keys) == 1 and set(next(iter(keys))) == set(CallRecord.model_fields)  # same shape always
    assert data["run"]["calls_failed"] == 2


def test_long_transcript_is_truncated_and_flagged(tmp_path, fake):
    path = tmp_path / "call_long.txt"
    path.write_text("\n".join(f"Customer: line {i} " + "words " * 40 for i in range(800)))
    rec = analyse_call(path, fake(valid_answer()), PROMPTS, SETTINGS)
    assert rec.quality.truncated and any("too long" in r for r in rec.review_reasons)


def test_cli_rejects_missing_folder_and_remote_servers(tmp_path):
    assert cli.main([str(tmp_path / "nope")]) == cli.EXIT_SETUP
    (tmp_path / "call_1.txt").write_text("Agent: hi")
    assert cli.main([str(tmp_path), "--ollama-url", "https://api.example.com"]) == cli.EXIT_SETUP


def test_prompt_version_changes_when_prompt_changes(tmp_path):
    for name in ("system.md", "user_template.md", "repair.md", "VERSION"):
        shutil.copy(PROMPTS_DIR / name, tmp_path / name)
    before = Prompts.load(tmp_path).version
    (tmp_path / "system.md").write_text("changed")
    assert Prompts.load(tmp_path).version != before


def test_published_json_schema_is_up_to_date():
    from callanalytics.config import REPO_ROOT
    from callanalytics.schema import OutputFile

    published = json.loads((REPO_ROOT / "schema" / "record.schema.json").read_text())
    assert published == OutputFile.model_json_schema(), "run: python -m callanalytics.schema"


def test_insights_without_a_real_quote_are_flagged(fake):
    answer = valid_answer(insights=[{"category": "repeat_contact", "text": "Second call.",
                                     "quote": "This is the second time I've called"}])
    rec = analyse_call(DATA / "call_005.txt", fake(answer), PROMPTS, SETTINGS)
    assert not rec.insights[0].verified
    assert any("insight quote" in r for r in rec.review_reasons)


def test_references_get_one_format_and_duplicates_are_removed(fake):
    answer = valid_answer(references=[{"type": "refund", "value": "R-F-22068"}, {"type": "refund", "value": "RF22068"}])
    rec = analyse_call(DATA / "call_005.txt", fake(answer), PROMPTS, SETTINGS)
    assert [r.value for r in rec.references] == ["RF-22068"] and rec.references[0].verified
