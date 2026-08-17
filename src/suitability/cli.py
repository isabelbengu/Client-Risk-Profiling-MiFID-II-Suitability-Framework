"""Command line interface.

    python -m suitability assess examples/clients/margherita.yaml
    python -m suitability assess examples/clients/margherita.yaml --report out.md --audit audit.jsonl
    python -m suitability questionnaire --section B
    python -m suitability portfolios
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import yaml

from . import audit as audit_mod
from . import report as report_mod
from .config import load_config
from .engine import assess
from .models import ClientCase


def _load_case(path: str) -> ClientCase:
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    members = [
        ClientCase(
            client_ref=m["client_ref"],
            answers=m["answers"],
            assessed_at=raw.get("assessed_at", ""),
        )
        for m in raw.get("group_members", [])
    ]
    return ClientCase(
        client_ref=raw["client_ref"],
        answers=raw.get("answers", {}),
        assessed_at=raw.get("assessed_at", ""),
        adviser_ref=raw.get("adviser_ref"),
        previous_final_band=raw.get("previous_final_band"),
        profile_updated_days_ago=raw.get("profile_updated_days_ago"),
        group_members=members,
    )


def _summary(outcome: Any, cfg: Any) -> str:
    lines = [
        f"client            : {outcome.client_ref}",
        f"status            : {outcome.status.upper()}",
        f"final risk band   : {outcome.final_band} ({cfg.band_label(outcome.final_band)})",
        f"binding constraint: {outcome.binding_constraint}",
        f"knowledge gate    : complexity tier {outcome.complexity_gate_tier}",
        "",
        "dimensions:",
    ]
    for name, d in outcome.dimensions.items():
        score = "-" if d.score is None else f"{d.score:5.1f}"
        caps = f"  [{'; '.join(d.caps_applied)}]" if d.caps_applied else ""
        lines.append(f"  {name:<10} score {score}   band {d.band}{caps}")
    lines.append("")
    if outcome.controls:
        lines.append("coherence controls triggered:")
        for c in outcome.controls:
            lines.append(f"  {c.id} {c.severity:<6} {c.name} - {c.detail}")
    else:
        lines.append("coherence controls triggered: none")
    lines.append("")
    r = outcome.recommendation
    if r.portfolio_id:
        lines.append(f"recommendation    : {r.portfolio_id} - {r.name}")
    else:
        lines.append("recommendation    : none")
    for line in r.rationale:
        lines.append(f"  * {line}")
    lines.append(f"sustainability    : {r.sustainability_status} - {r.sustainability_detail}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="suitability", description=__doc__)
    parser.add_argument("--config-dir", default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    p_assess = sub.add_parser("assess", help="run a suitability assessment")
    p_assess.add_argument("case")
    p_assess.add_argument("--report", help="write the Art. 54(12) suitability report here")
    p_assess.add_argument("--audit", help="append the audit record to this JSONL file")
    p_assess.add_argument("--json", action="store_true", help="print the outcome as JSON")

    p_q = sub.add_parser("questionnaire", help="print the questionnaire")
    p_q.add_argument("--section", default=None)

    sub.add_parser("portfolios", help="print the model portfolio universe")
    sub.add_parser("controls", help="print the coherence controls")

    args = parser.parse_args(argv)
    cfg = load_config(args.config_dir)

    if args.command == "assess":
        case = _load_case(args.case)
        outcome = assess(case, cfg)
        answers = case.answers if not case.group_members else case.group_members[0].answers
        text = report_mod.render(outcome, {**answers, **case.answers}, cfg)

        if args.json:
            print(json.dumps(outcome.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(_summary(outcome, cfg))

        if args.report:
            with open(args.report, "w", encoding="utf-8") as fh:
                fh.write(text)
            print(f"\nsuitability report written to {args.report}", file=sys.stderr)
        if args.audit:
            rec = audit_mod.build_record(outcome, answers, case.adviser_ref, text)
            audit_mod.append(rec, args.audit)
            print(f"audit record appended to {args.audit}", file=sys.stderr)
        return 0 if outcome.status in ("recommended", "referred") else 1

    if args.command == "questionnaire":
        for section in cfg.questionnaire["sections"]:
            if args.section and section["id"] != args.section:
                continue
            print(f"\n== Section {section['id']}: {section['name']} ==")
            for basis in section.get("regulatory_basis", []) or []:
                print(f"   [{basis}]")
            for q in section.get("questions", []):
                print(f"\n {q['id']}. {q['text']}")
                for opt in q.get("options", []) or []:
                    marker = "*" if opt.get("correct") else "-"
                    score = f"  ({opt['score']})" if opt.get("score") is not None else ""
                    print(f"    {marker} {opt['label']}{score}")
        return 0

    if args.command == "portfolios":
        header = f"{'id':<10} {'band':<5} {'sri':<4} {'stress':<7} {'horiz':<6} {'tier':<5} {'bps':<5} name"
        print(header)
        print("-" * len(header))
        for p in cfg.all_portfolios():
            print(
                f"{p['id']:<10} {p['risk_band']:<5} {p['sri']:<4} {p['stress_loss_pct']:<7} "
                f"{p['min_horizon_years']:<6} {p['complexity_tier']:<5} {p['total_cost_bps']:<5} {p['name']}"
            )
        return 0

    if args.command == "controls":
        for c in cfg.scoring["coherence_controls"]:
            print(f"{c['id']}  {c['severity']:<6}  {c['name']}")
            print(f"        basis : {c['basis']}")
            print(f"        effect: {c['effect']}\n")
        return 0

    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
