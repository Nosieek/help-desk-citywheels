"""
Run the agent on every question in questions.json and check the answers.

Usage (after `pip install -e .`, with ANTHROPIC_API_KEY set):

    python eval/run_eval.py

Writes eval/results.md with a pass/fail table and the full answers.

Check fields per question (all optional):
- expected_tools:           every listed tool must appear in the trace
- expected_tools_any:       at least one listed tool must appear
- answer_contains:          items that must appear in the answer
                            (a string = required; a list = any one of the
                            alternatives is enough); case-insensitive
- answer_must_not_contain:  none of these may appear in the answer
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from agent.config import MODEL
from agent.loop import run_agent

QUESTIONS_PATH = Path(__file__).parent / "questions.json"
RESULTS_PATH = Path(__file__).parent / "results.md"


def check_question(question: dict, answer: str, called_tools: list[str]) -> list[str]:
    """Return a list of failed checks (empty list = pass)."""
    failures = []
    answer_lower = answer.lower()

    for tool in question.get("expected_tools", []):
        if tool not in called_tools:
            failures.append(f"tool `{tool}` was not called (called: {called_tools or 'none'})")

    tools_any = question.get("expected_tools_any", [])
    if tools_any and not any(tool in called_tools for tool in tools_any):
        failures.append(f"none of {tools_any} was called (called: {called_tools or 'none'})")

    for item in question.get("answer_contains", []):
        alternatives = [item] if isinstance(item, str) else item
        if not any(alt.lower() in answer_lower for alt in alternatives):
            failures.append(f"answer does not contain any of: {alternatives}")

    for text in question.get("answer_must_not_contain", []):
        if text.lower() in answer_lower:
            failures.append(f"answer contains forbidden text: `{text}`")

    return failures


def run():
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    rows = []
    passed = 0

    for question in questions:
        print(f"[{question['id']}] {question['question']}")
        try:
            result = run_agent(question["question"])
            answer = result.answer
            called_tools = [call["tool"] for call in result.tool_calls]
            failures = check_question(question, answer, called_tools)
        except Exception as e:
            answer = ""
            called_tools = []
            failures = [f"agent raised an exception: {e}"]

        status = "PASS" if not failures else "FAIL"
        if not failures:
            passed += 1
        print(f"  -> {status}" + (f": {'; '.join(failures)}" if failures else ""))

        rows.append({
            "question": question,
            "answer": answer,
            "tools": called_tools,
            "failures": failures,
        })

    write_results(rows, passed)
    print(f"\n{passed}/{len(rows)} passed. Results written to {RESULTS_PATH}")


def write_results(rows: list[dict], passed: int):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Evaluation results",
        "",
        f"- Run: {now}",
        f"- Model: `{MODEL}`",
        f"- Result: **{passed}/{len(rows)} passed**",
        "",
        "| # | Question | Tools called | Status |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        q = row["question"]
        status = "PASS" if not row["failures"] else "FAIL"
        tools = ", ".join(row["tools"]) or "—"
        lines.append(f"| {q['id']} | {q['question']} | {tools} | {status} |")

    lines += ["", "## Details", ""]
    for row in rows:
        q = row["question"]
        lines.append(f"### {q['id']}")
        lines.append("")
        lines.append(f"**Q:** {q['question']}")
        lines.append("")
        lines.append(f"**Expected:** {q['note']}" if "note" in q else "")
        lines.append("")
        answer = row["answer"].replace("\n", " ").strip()
        if len(answer) > 400:
            answer = answer[:400] + " […]"
        lines.append(f"**A:** {answer}")
        lines.append("")
        if row["failures"]:
            lines.append("**Failed checks:**")
            for failure in row["failures"]:
                lines.append(f"- {failure}")
            lines.append("")

    RESULTS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    run()
