#!/usr/bin/env python3
"""
Evaluation Module for Multi-Modal Evidence Review System
=========================================================
Runs the main pipeline on sample_claims.csv, compares against expected
outputs, computes per-field accuracy, and generates evaluation_report.md.

Usage:
    python evaluation/main.py                   # full run: process + evaluate
    python evaluation/main.py --skip-run         # evaluate existing output only
    python evaluation/main.py --predictions FILE # evaluate a specific predictions CSV
"""

import csv
import json
import os
import sys
import time
import argparse
from pathlib import Path
from collections import defaultdict

# Add parent directory so we can import main
CODE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE_DIR))

BASE_DIR = CODE_DIR.parent
DATASET_DIR = BASE_DIR / "dataset"
SAMPLE_FILE = DATASET_DIR / "sample_claims.csv"
EVAL_DIR = Path(__file__).resolve().parent
SAMPLE_OUTPUT = EVAL_DIR / "sample_predictions.csv"

# ---------------------------------------------------------------------------
# Fields & evaluation config
# ---------------------------------------------------------------------------

EXACT_MATCH_FIELDS = [
    "evidence_standard_met",
    "claim_status",
    "issue_type",
    "object_part",
    "valid_image",
    "severity",
]

SET_FIELDS = [
    "risk_flags",
    "supporting_image_ids",
]

ALL_EVALUATED_FIELDS = EXACT_MATCH_FIELDS + SET_FIELDS

# Weights for the weighted-average score (higher = more important)
FIELD_WEIGHTS = {
    "claim_status": 3.0,
    "issue_type": 2.0,
    "object_part": 2.0,
    "evidence_standard_met": 1.5,
    "valid_image": 1.0,
    "severity": 1.5,
    "risk_flags": 1.5,
    "supporting_image_ids": 1.0,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_csv(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def norm_set(value: str) -> set[str]:
    """Normalise a semicolon-separated field into a lowercase set."""
    if not value or value.strip().lower() == "none":
        return set()
    return {v.strip().lower() for v in value.split(";") if v.strip()}


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ---------------------------------------------------------------------------
# Core evaluation
# ---------------------------------------------------------------------------

def evaluate(predicted: list[dict], expected: list[dict]):
    """Compare row-by-row, return (metrics, details)."""

    n = min(len(predicted), len(expected))
    if len(predicted) != len(expected):
        print(f"⚠  Row count mismatch: predicted={len(predicted)}, expected={len(expected)}")

    correct = defaultdict(int)
    total = defaultdict(int)
    set_sims = defaultdict(list)
    details: list[dict] = []

    for i in range(n):
        pred, exp = predicted[i], expected[i]
        row_info: dict = {"row": i + 1, "user_id": exp.get("user_id", "?"), "misses": {}}

        # exact-match fields
        for f in EXACT_MATCH_FIELDS:
            pv = str(pred.get(f, "")).lower().strip()
            ev = str(exp.get(f, "")).lower().strip()
            ok = pv == ev
            correct[f] += int(ok)
            total[f] += 1
            if not ok:
                row_info["misses"][f] = {"pred": pv, "exp": ev}

        # set fields
        for f in SET_FIELDS:
            ps = norm_set(pred.get(f, ""))
            es = norm_set(exp.get(f, ""))
            sim = jaccard(ps, es)
            set_sims[f].append(sim)
            exact = ps == es
            correct[f] += int(exact)
            total[f] += 1
            if not exact:
                row_info["misses"][f] = {
                    "pred": sorted(ps) if ps else ["none"],
                    "exp": sorted(es) if es else ["none"],
                    "jaccard": f"{sim:.2f}",
                }

        details.append(row_info)

    # aggregate
    metrics = {}
    weighted_sum, weight_total = 0.0, 0.0
    for f in ALL_EVALUATED_FIELDS:
        acc = correct[f] / total[f] if total[f] else 0
        w = FIELD_WEIGHTS.get(f, 1.0)
        weighted_sum += acc * w
        weight_total += w
        metrics[f] = {"accuracy": acc, "correct": correct[f], "total": total[f]}

    metrics["overall_accuracy"] = sum(
        metrics[f]["accuracy"] for f in ALL_EVALUATED_FIELDS
    ) / len(ALL_EVALUATED_FIELDS)

    metrics["weighted_accuracy"] = weighted_sum / weight_total if weight_total else 0

    for f in SET_FIELDS:
        sims = set_sims[f]
        metrics[f + "_jaccard_avg"] = sum(sims) / len(sims) if sims else 0

    return metrics, details


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(
    metrics: dict,
    details: list[dict],
    runtime_stats: dict | None = None,
) -> str:
    """Produce Markdown evaluation report."""

    lines = [
        "# Evaluation Report",
        "",
        "## Per-Field Accuracy",
        "",
        "| Field | Accuracy | Correct | Total |",
        "|---|---|---|---|",
    ]

    for f in ALL_EVALUATED_FIELDS:
        m = metrics[f]
        lines.append(f"| `{f}` | **{m['accuracy']:.1%}** | {m['correct']} | {m['total']} |")

    lines += [
        "",
        f"**Overall Mean Accuracy: {metrics['overall_accuracy']:.1%}**",
        "",
        f"**Weighted Accuracy: {metrics['weighted_accuracy']:.1%}**",
        "",
    ]

    # set similarities
    lines += ["## Set-Field Jaccard Similarity", ""]
    for f in SET_FIELDS:
        k = f + "_jaccard_avg"
        lines.append(f"- **`{f}`**: {metrics.get(k, 0):.3f}")
    lines.append("")

    # mismatches
    lines += ["## Detailed Mismatches", ""]
    any_miss = False
    for row in details:
        if row["misses"]:
            any_miss = True
            lines.append(f"### Row {row['row']} — `{row['user_id']}`")
            for field, info in row["misses"].items():
                if isinstance(info.get("pred"), list):
                    lines.append(
                        f"- **{field}**: predicted `{';'.join(info['pred'])}` "
                        f"vs expected `{';'.join(info['exp'])}` "
                        f"(Jaccard {info.get('jaccard', 'N/A')})"
                    )
                else:
                    lines.append(
                        f"- **{field}**: predicted `{info['pred']}` "
                        f"vs expected `{info['exp']}`"
                    )
            lines.append("")
    if not any_miss:
        lines.append("_All predictions matched expected values._\n")

    # operational analysis
    lines += [
        "## Operational Analysis",
        "",
    ]

    if runtime_stats:
        lines += [
            f"- **Model**: {runtime_stats.get('model', 'meta-llama/llama-4-scout-17b-16e-instruct')}",
            f"- **Model calls (sample set)**: {runtime_stats.get('total_requests', 'N/A')}",
            f"- **Input tokens**: ~{runtime_stats.get('total_input_tokens', 'N/A'):,}",
            f"- **Output tokens**: ~{runtime_stats.get('total_output_tokens', 'N/A'):,}",
            f"- **Images processed**: {runtime_stats.get('images_processed', 'N/A')}",
            f"- **Runtime**: {runtime_stats.get('runtime_s', 'N/A'):.1f}s "
            f"({runtime_stats.get('runtime_s', 0)/60:.1f}m)",
            "",
            "### Full test-set cost projection",
            "",
            f"- **Test claims**: 45 rows",
            f"- **Estimated model calls**: 45 (one per claim)",
            f"- **Estimated input tokens**: "
            f"~{int(runtime_stats.get('total_input_tokens',0)/max(runtime_stats.get('total_requests',1),1)*45):,}",
            f"- **Estimated output tokens**: "
            f"~{int(runtime_stats.get('total_output_tokens',0)/max(runtime_stats.get('total_requests',1),1)*45):,}",
            f"- **Cost**: $0.00 (Groq free tier)",
            f"- **Estimated runtime**: "
            f"~{runtime_stats.get('runtime_s', 0)/max(runtime_stats.get('total_requests',1),1)*45:.0f}s",
            "",
            "### Rate-limit & efficiency strategy",
            "",
            "- 2.0 s delay between API calls (well within 60 RPM free-tier limit)",
            "- One VLM call per claim (all images sent together)",
            "- Key Rotation (automatically rotates through GROQ_API_KEYS)",
            "- Model Rotation (automatically rotates through working models on 429 errors)",
            "- JSON response mode avoids output parsing failures",
            "- Low temperature (0.1) for deterministic outputs",
            "",
        ]
    else:
        lines += [
            "> Runtime stats not available (run with `--skip-run` disabled "
            "to collect them).",
            "",
        ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Evaluate the evidence-review system")
    ap.add_argument("--skip-run", action="store_true",
                    help="Skip running the system; evaluate existing predictions only")
    ap.add_argument("--predictions", type=str,
                    help="Path to a predictions CSV to evaluate (implies --skip-run)")
    ap.add_argument("--model", type=str, default=None,
                    help="Model override for the processing run")
    args = ap.parse_args()

    runtime_stats: dict | None = None
    pred_path = Path(args.predictions) if args.predictions else SAMPLE_OUTPUT

    if args.predictions:
        args.skip_run = True

    # --- Step 1: Run the system on sample_claims.csv ---
    if not args.skip_run:
        print("=" * 60)
        print("Step 1: Running system on sample_claims.csv")
        print("=" * 60)

        from main import GroqClient, process_claims, API_KEYS, MODEL_NAME

        keys = API_KEYS
        if not keys:
            print("ERROR: GROQ_API_KEY or GROQ_API_KEYS not set.")
            sys.exit(1)

        model = args.model or MODEL_NAME
        client = GroqClient(api_keys=keys, model_name=model)

        t0 = time.time()
        results, n_images = process_claims(SAMPLE_FILE, pred_path, client)
        elapsed = time.time() - t0

        st = client.stats
        runtime_stats = {
            "model": model,
            "total_requests": st["total_requests"],
            "total_input_tokens": st["total_input_tokens"],
            "total_output_tokens": st["total_output_tokens"],
            "images_processed": n_images,
            "runtime_s": elapsed,
        }
        print(f"\nPredictions written to {pred_path}\n")

    # --- Step 2: Evaluate ---
    print("=" * 60)
    print("Step 2: Evaluating predictions vs expected")
    print("=" * 60)

    if not pred_path.exists():
        print(f"ERROR: Predictions file not found: {pred_path}")
        print("Run without --skip-run first.")
        sys.exit(1)

    predicted = load_csv(pred_path)
    expected = load_csv(SAMPLE_FILE)

    metrics, details = evaluate(predicted, expected)

    # pretty print
    print(f"\n{'Field':<30} {'Accuracy':>10} {'Correct':>8} {'Total':>6}")
    print("-" * 58)
    for f in ALL_EVALUATED_FIELDS:
        m = metrics[f]
        print(f"{f:<30} {m['accuracy']:>9.1%} {m['correct']:>8} {m['total']:>6}")
    print("-" * 58)
    print(f"{'Overall Mean':<30} {metrics['overall_accuracy']:>9.1%}")
    print(f"{'Weighted':<30} {metrics['weighted_accuracy']:>9.1%}")

    # --- Step 3: Write report ---
    report = generate_report(metrics, details, runtime_stats)
    report_path = EVAL_DIR / "evaluation_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\nReport saved -> {report_path}")


if __name__ == "__main__":
    main()
