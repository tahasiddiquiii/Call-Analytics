import json
import shutil

from callanalytics import __main__ as cli
from callanalytics.config import PROMPTS_DIR, REPO_ROOT, Settings
from callanalytics.pipeline import Prompts, analyse_call, run
from callanalytics.schema import CallRecord, OutputFile
from tests.conftest import DATA, FIXTURES, actions, classify, judge

SETTINGS = Settings()
PROMPTS = Prompts.load()


def test_valid_answers_become_ok_record(fake):
    rec = analyse_call(DATA / "call_005.txt", fake(), PROMPTS, SETTINGS)
    assert rec.status == "ok" and rec.call_id == "call_005"
    assert rec.client_brand == "Northwave Mobile" and rec.agent_name == "Aaron"
    assert rec.outcome.status == "resolved"
    assert [(r.type, r.value) for r in rec.references] == [("refund", "RF-22068")]  # found by code
    assert rec.sentiment.trajectory == "improved"
    assert rec.quality.model_requests == 3


def test_outcome_status_comes_from_the_rule_not_the_model(fake):
    cases = [
        (dict(handed_over=True), "escalated"),
        (dict(solution_agreed=False), "unresolved"),
        (dict(needs_future_step=True), "resolved_pending_action"),
        (dict(handed_over=True, solution_agreed=False), "escalated"),
    ]
    for answers, expected in cases:
        rec = analyse_call(DATA / "call_005.txt", fake(judge=judge(**answers)), PROMPTS, SETTINGS)
        assert rec.outcome.status == expected, answers
        assert rec.outcome.basis is not None


def test_non_customer_calls_are_normalised_and_skip_the_actions_task(fake):
    client = fake(classify=classify(call_type="test_call", intent={"primary": "general_inquiry",
                                                                   "secondary": [], "detail": "QA test."}))
    rec = analyse_call(DATA / "call_004.txt", client, PROMPTS, SETTINGS)
    assert rec.intent.primary == "non_customer_call" and rec.outcome.status == "not_applicable"
    assert rec.outcome.basis is None and rec.supervisor_priority == "low"
    assert rec.quality.rule_corrections and rec.quality.model_requests == 2
    assert [c[0] for c in client.calls] == ["classify", "judge"]


def test_invented_quotes_trigger_review(fake):
    client = fake(judge=judge(outcome_quote="I approve everything forever"),
                  actions=actions(insights=[{"category": "process_gap", "text": "App gave no warning.",
                                             "quote": "The app warned me twice"}]))
    rec = analyse_call(DATA / "call_005.txt", client, PROMPTS, SETTINGS)
    assert rec.needs_review
    assert not rec.insights[0].verified and not rec.evidence[-1].verified
    assert any("insight quote" in r for r in rec.review_reasons)


def test_personal_data_is_removed_from_text_fields(fake):
    client = fake(classify=classify(summary="Carla Mendes (Mr. Mendes' wife) paid with card ending in 4471."),
                  judge=judge(outcome_detail="Refund sent; call 555 0194 123 or dana dot w at example dot com."))
    rec = analyse_call(DATA / "call_005.txt", client, PROMPTS, SETTINGS)
    text = rec.summary + rec.outcome.detail
    for leaked in ("Carla", "Mendes", "4471", "0194", "example dot com"):
        assert leaked not in text
    assert rec.quality.redactions >= 4


def test_invalid_json_is_repaired_on_second_attempt(fake):
    client = fake(classify=["{not json", classify()])
    rec = analyse_call(DATA / "call_005.txt", client, PROMPTS, SETTINGS)
    assert rec.status == "ok" and rec.quality.model_requests == 4
    repair_messages = [m for task, m in client.calls if task == "classify"][1]
    assert "could not be used" in repair_messages[-1]["content"]


def test_wrong_enum_value_fails_cleanly(fake):
    rec = analyse_call(DATA / "call_005.txt", fake(judge=judge(sentiment_end="furious")), PROMPTS, SETTINGS)
    assert rec.status == "failed" and rec.needs_review
    assert rec.summary is None and rec.action_items == []
    assert "schema" in rec.error


def test_model_timeout_gives_failed_record(fake, model_error):
    rec = analyse_call(DATA / "call_005.txt", fake(actions=model_error), PROMPTS, SETTINGS)
    assert rec.status == "failed" and "600s" in rec.error


def test_flags_come_from_yes_no_answers_and_contradicting_insights_are_dropped(fake):
    insights = [{"category": "compliance_risk", "text": "Agent guaranteed approval.",
                 "quote": "I guarantee it, no deductible either"},
                {"category": "churn_risk", "text": "May leave.", "quote": "Okay, wow. Okay."}]
    client = fake(judge=judge(agent_overpromised=True), actions=actions(insights=insights))
    rec = analyse_call(DATA / "call_006.txt", client, PROMPTS, SETTINGS)
    assert rec.flags.compliance_risk and not rec.flags.churn_risk
    assert [i.category for i in rec.insights] == ["compliance_risk"]  # churn insight contradicted -> dropped
    assert any("dropped churn_risk" in c for c in rec.quality.rule_corrections)
    assert rec.supervisor_priority == "high"


def test_judge_prompt_shows_the_customers_first_and_last_turns(fake):
    client = fake()
    rec = analyse_call(DATA / "call_002.txt", client, PROMPTS, SETTINGS)
    judge_prompt = [m for task, m in client.calls if task == "judge"][0][1]["content"]
    assert "I want to cancel my internet" in judge_prompt and "Don't make me call back" in judge_prompt
    sentiment = [e for e in rec.evidence if e.supports == "sentiment"]
    assert len(sentiment) == 2 and all(e.verified for e in sentiment)


def test_text_null_due_dates_become_real_nulls(fake):
    items = [{"owner": "agent", "task": "Do it", "due": "null"}, {"owner": "customer", "task": "Call", "due": "Monday"}]
    rec = analyse_call(DATA / "call_005.txt", fake(actions=actions(action_items=items)), PROMPTS, SETTINGS)
    assert [a.due for a in rec.action_items] == [None, "Monday"]


def test_run_never_stops_on_bad_files_and_output_is_consistent(tmp_path, fake, model_error):
    folder = tmp_path / "calls"
    folder.mkdir()
    shutil.copy(FIXTURES / "edge" / "empty.txt", folder / "call_a.txt")
    shutil.copy(FIXTURES / "edge" / "messy.txt", folder / "call_b.txt")
    shutil.copy(DATA / "call_005.txt", folder / "call_c.txt")
    out = tmp_path / "out" / "records.json"
    # call_b gets good answers; call_c's first task fails twice
    client = fake(classify=[classify(), model_error, model_error])
    run(folder, out, client, SETTINGS, runtime="test")

    data = json.loads(out.read_text())
    OutputFile.model_validate(data)  # whole file matches the published schema
    recs = {r["call_id"]: r for r in data["records"]}
    assert list(recs) == ["call_a", "call_b", "call_c"]
    assert recs["call_a"]["status"] == "failed"  # empty file
    assert recs["call_b"]["status"] == "ok" and recs["call_b"]["needs_review"]  # messy lines flagged
    assert recs["call_c"]["status"] == "failed"
    keys = {tuple(r.keys()) for r in data["records"]}
    assert len(keys) == 1 and set(next(iter(keys))) == set(CallRecord.model_fields)  # same shape always
    assert data["run"]["calls_failed"] == 2


def test_long_transcript_is_truncated_and_flagged(tmp_path, fake):
    path = tmp_path / "call_long.txt"
    path.write_text("\n".join(f"Customer: line {i} " + "words " * 40 for i in range(800)))
    rec = analyse_call(path, fake(), PROMPTS, SETTINGS)
    assert rec.quality.truncated and any("too long" in r for r in rec.review_reasons)


def test_cli_rejects_missing_folder_and_remote_servers(tmp_path):
    assert cli.main([str(tmp_path / "nope")]) == cli.EXIT_SETUP
    (tmp_path / "call_1.txt").write_text("Agent: hi")
    assert cli.main([str(tmp_path), "--ollama-url", "https://api.example.com"]) == cli.EXIT_SETUP


def test_prompt_version_changes_when_prompt_changes(tmp_path):
    for p in PROMPTS_DIR.iterdir():
        shutil.copy(p, tmp_path / p.name)
    before = Prompts.load(tmp_path).version
    (tmp_path / "task_judge.md").write_text("changed")
    assert Prompts.load(tmp_path).version != before


def test_published_json_schema_is_up_to_date():
    published = json.loads((REPO_ROOT / "schema" / "record.schema.json").read_text())
    assert published == OutputFile.model_json_schema(), "run: python -m callanalytics.schema"
