#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

ALLOWED_CATEGORIES = {"sales", "labor", "inventory", "training", "customer_experience"}


def load_csv(name):
    with (DATA / name).open(newline="") as handle:
        return list(csv.DictReader(handle))


def severity_for_training(completion_pct, target_pct):
    gap = target_pct - completion_pct
    if gap >= 10:
        return "high"
    if gap > 0:
        return "medium"
    return "low"


def build_briefing(region):
    metrics = [row for row in load_csv("store_metrics.csv") if row["region"] == region]
    schedules = {row["store_id"]: row for row in load_csv("schedules.csv")}
    inventory = load_csv("inventory.csv")
    playbooks = json.loads((DATA / "confluence_playbooks.json").read_text())
    target_training = playbooks["FY26 Store Operations Goals"]["training_completion_target_pct"]
    target_wait = playbooks["FY26 Store Operations Goals"]["customer_wait_target_minutes"]

    issues = []

    for row in metrics:
        store_id = row["store_id"]
        completion = float(row["training_completion_pct"])
        if completion < target_training:
            schedule = schedules.get(store_id, {})
            severity = severity_for_training(completion, target_training)
            issues.append(
                {
                    "store": f'{store_id} — {row["store_name"]}',
                    "severity": severity,
                    "category": "training",
                    "evidence": f'Training completion is {completion:.0f}% versus the FY26 {target_training}% target; {schedule.get("converted_training_hours", "0")} hours were converted for {schedule.get("conversion_reason", "coverage")}.',
                    "recommended_action": "Protect training blocks this week and review rush-window staffing coverage.",
                }
            )

        wait = float(row["avg_wait_minutes"])
        if wait > target_wait:
            issues.append(
                {
                    "store": f'{store_id} — {row["store_name"]}',
                    "severity": "medium" if wait < 8 else "high",
                    "category": "customer_experience",
                    "evidence": f'Average wait time is {wait:.1f} minutes versus the FY26 {target_wait}-minute target; customer satisfaction is {row["customer_satisfaction"]}.',
                    "recommended_action": "Review queue staffing and peak-window service flow.",
                }
            )

    for row in inventory:
        if row["stockout_risk"] == "high" and any(metric["store_id"] == row["store_id"] for metric in metrics):
            metric = next(metric for metric in metrics if metric["store_id"] == row["store_id"])
            issues.append(
                {
                    "store": f'{row["store_id"]} — {metric["store_name"]}',
                    "severity": "high",
                    "category": "inventory",
                    "evidence": f'{row["ingredient"]} has {row["on_hand_units"]} units on hand against {row["forecast_7d_units"]} forecast units and a {row["reorder_eta_days"]}-day reorder ETA.',
                    "recommended_action": "Expedite an inter-store transfer or vendor escalation before the next delivery cutoff.",
                }
            )

    severity_order = {"high": 0, "medium": 1, "low": 2}
    return sorted(issues, key=lambda issue: (severity_order[issue["severity"]], issue["store"], issue["category"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="Pacific")
    args = parser.parse_args()

    issues = build_briefing(args.region)
    print(f"Weekly {args.region} Regional Risk Briefing")
    print()
    for issue in issues:
        assert issue["category"] in ALLOWED_CATEGORIES
        print(f'- Store: {issue["store"]}')
        print(f'  Severity: {issue["severity"]}')
        print(f'  Category: {issue["category"]}')
        print(f'  Evidence: {issue["evidence"]}')
        print(f'  Recommended action: {issue["recommended_action"]}')
        print()

    high = [issue for issue in issues if issue["severity"] == "high"]
    if high:
        stores = ", ".join(issue["store"].split(" — ")[0] for issue in high)
        print(f"I found {len(high)} high-severity risks. Do you approve creating OpsTask tickets for stores {stores}?")


if __name__ == "__main__":
    main()
