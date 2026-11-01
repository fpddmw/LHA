"""Human-readable projection of recorded work, without retrospective model claims."""
import html
import json
import os
from pathlib import Path
from .common import load


def report(output, state):
    output = Path(output)
    def relative(path):
        try:
            return Path(os.path.relpath(path, output)).as_posix()
        except ValueError:
            return Path(path).resolve().as_uri()
    def encoded(value):
        return json.dumps(value, ensure_ascii=False, indent=2)
    scope = "Recorded online work. Planner selection and Critic scores are not independent final evaluation."
    if state["config"]["execution"].get("mode") == "replay":
        scope += " Replay execution uses archived or synthetic media and may use scripted responses; it is not new generation or quality evidence."
    md = ["# Creative loop record", "", scope, ""]
    body = ["<h1>Creative loop record</h1><p>" + html.escape(scope) + "</p>"]
    def section(title, value):
        md.extend(["## " + title, "", "```json", encoded(value), "```", ""])
        body.append("<h2>" + html.escape(title) + "</h2><pre>" + html.escape(encoded(value)) + "</pre>")
    section("Outcome", {k: state.get(k) for k in ("status", "delivery_candidate", "final", "pending_tool", "unresolved_jobs", "last_error")})
    section("Original request", state["request"]["text"])
    section("Working notes and workspace", {k: state.get(k) for k in ("notes", "workspace")})
    section("Actual knowledge reads", state.get("reads", {}))
    from .experience_usage import project_run, write_json
    try:
        usage = project_run(output)
        write_json(output / "experience-usage.json", usage)
        section("Experience use (factual provenance, not effectiveness)", {
            "record": "experience-usage.json", "calls": usage["calls"],
            "surfaces": usage["surfaces"], "model_references": usage["model_references"], "issues": usage["issues"]})
        body.append('<p><a href="experience-usage.json">Complete experience-use record</a></p>')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        section("Experience-use projection unavailable", {"error_type": type(exc).__name__,
                "note": "Original operations remain available; missing projection is not zero use."})
    section("Exact generation requests", [{"job_id": k, "input_video": j["payload"]["input_id"],
        "prompt": j["payload"]["prompt"], "renderer": j["payload"]["renderer"]}
        for k, j in state["jobs"].items() if j["kind"] == "generate"])
    section("Candidates, ancestry and recorded execution costs", state["videos"])
    body.append("<h2>Videos</h2>")
    md.extend(["## Videos", ""])
    for identity, video in state["videos"].items():
        path = relative(video["path"])
        md.append(f"- [{identity}]({path})")
        body.append(f'<h3>{html.escape(identity)}</h3><video controls preload="metadata" src="{html.escape(path, quote=True)}"></video>')
    md.append("")
    section("Online Critic reports (not final scores)", {k: {"video": v["video_id"], "report": v["report"],
        "profile_sha256": v["profile_sha256"], "request_path": v.get("request_path")}
        for k, v in state["evaluations"].items()})
    for identity, feedback in state["evaluations"].items():
        cited = set()
        report = feedback["report"]
        for row in list(report["main_scores"].values()) + report["comparisons"] + report["extra_checks"]:
            cited.update(row["evidence_refs"])
        body.append("<details><summary>Cited evidence: " + html.escape(identity) + "</summary>")
        for frame in feedback.get("evidence", []):
            if frame["id"] in cited:
                body.append(f'<figure><img loading="lazy" src="{html.escape(relative(frame["path"]), quote=True)}"><figcaption>{html.escape(frame["id"])}</figcaption></figure>')
        body.append("</details>")
    section("Observed intervals and frames", state["observations"])
    section("Recovery and interruptions", {k: state.get(k, []) for k in
        ("recoveries", "resource_changes", "delivery_continuations", "interruption_history")})
    failures = []
    for identity in state["jobs"]:
        path = output / "jobs" / identity / "response.json"
        if path.exists():
            response = load(path)
            if response.get("status") == "failed":
                failures.append({"job_id": identity, "response": response})
    section("Recorded tool failures", failures)
    body.append("<h2>Operations and model exchanges</h2>")
    md.extend(["## Operations and model exchanges", ""])
    for event in state["events"]:
        identity = event["event_id"]
        title = identity + ": " + str(event.get("request", {}).get("action", event["status"]))
        links = []
        for path, label in ((output / "events" / (identity + ".json"), "Operation"),
                            (output / "calls" / identity / "input.json", "Model input"),
                            (output / "calls" / identity / "response.txt", "Model response")):
            if path.exists():
                url = relative(path)
                links.append(f'<a href="{html.escape(url, quote=True)}">{label}</a>')
                md.append(f"- {title}: [{label}]({url})")
        body.append("<details><summary>" + html.escape(title) + "</summary>" + " | ".join(links)
                    + "<pre>" + html.escape(encoded(event.get("request", {}))) + "</pre></details>")
    body.append('<p><a href="state.json">Complete checkpoint</a> | <a href="report.md">Markdown record</a></p>')
    (output / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (output / "report.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Creative loop record</title>'
        '<style>body{font:16px system-ui;max-width:1150px;margin:32px auto;padding:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f6f8;padding:14px}video{max-width:650px;width:100%}img{max-width:450px;width:100%}details{margin:12px 0}figure{display:inline-block;margin:10px;max-width:450px}</style>'
        + "\n".join(body) + "</html>", encoding="utf-8")
