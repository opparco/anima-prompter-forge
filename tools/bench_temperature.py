#!/usr/bin/env python3
"""Benchmark LMStudioPrompter across temperature values and plot error rates.

Usage:
    python tools/bench_temperature.py
    python tools/bench_temperature.py --temps 0.5 0.9 1.1 --trials 5
    python tools/bench_temperature.py --concept "knight on horseback" --output out.png
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from anima_prompter.prompter import LMStudioError, LMStudioPrompter

_ERROR_TYPES = ["ok", "json_parse", "connection_error", "http_error", "other"]
_COLORS = {
    "ok": "#4caf50",
    "json_parse": "#ff9800",
    "connection_error": "#9e9e9e",
    "http_error": "#f44336",
    "other": "#9c27b0",
}


def _classify(e: LMStudioError) -> str:
    msg = str(e)
    if "No JSON object found" in msg:
        return "json_parse"
    if "returned HTTP" in msg:
        return "http_error"
    if "request failed" in msg:
        return "connection_error"
    return "other"


def _run_trial(prompter: LMStudioPrompter, concept: str, temperature: float) -> str:
    try:
        prompter.generate(concept, temperature=temperature)
        return "ok"
    except LMStudioError as e:
        return _classify(e)
    except Exception:
        return "other"


def _bench(temps: list[float], trials: int, prompter: LMStudioPrompter, concept: str) -> dict:
    results = {}
    for temp in temps:
        counts = {t: 0 for t in _ERROR_TYPES}
        for i in range(trials):
            outcome = _run_trial(prompter, concept, temp)
            counts[outcome] += 1
            print(f"  temp={temp:.2f}  trial {i + 1}/{trials}  → {outcome}")
        results[temp] = counts
    return results


def _print_table(results: dict) -> None:
    print(f"\n{'temp':>6}  " + "  ".join(f"{e:>14}" for e in _ERROR_TYPES))
    for temp in sorted(results):
        print(f"{temp:>6.2f}  " + "  ".join(f"{results[temp][e]:>14}" for e in _ERROR_TYPES))


def _plot(results: dict, trials: int, output: str) -> None:
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("\nmatplotlib not installed — skipping plot. Run: pip install matplotlib")
        return

    temps = sorted(results)
    x = np.arange(len(temps))

    fig, ax = plt.subplots(figsize=(max(8, len(temps) * 1.4), 5))
    bottoms = np.zeros(len(temps))

    for etype in _ERROR_TYPES:
        fracs = np.array([results[t][etype] / trials for t in temps])
        ax.bar(x, fracs, 0.6, bottom=bottoms, label=etype, color=_COLORS[etype])
        bottoms += fracs

    ax.set_xticks(x)
    ax.set_xticklabels([f"{t:.2f}" for t in temps])
    ax.set_xlabel("Temperature")
    ax.set_ylabel("Fraction of trials")
    ax.set_title("LM Studio response outcome by temperature")
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    print(f"\nSaved → {output}")
    plt.show()


def main() -> None:
    p = argparse.ArgumentParser(description="Benchmark LM Studio temperature vs error rate")
    p.add_argument("--url", default="http://localhost:1234", help="LM Studio base URL")
    p.add_argument("--concept", default="a girl under cherry blossoms", help="Prompt concept")
    p.add_argument("--temps", nargs="+", type=float, default=[0.1, 0.5, 0.9, 1.1])
    p.add_argument("--trials", type=int, default=5, help="Trials per temperature value")
    p.add_argument("--timeout", type=float, default=60.0, help="Per-request timeout in seconds")
    p.add_argument("--output", default="temp_error_correlation.png", help="Output image path")
    args = p.parse_args()

    prompter = LMStudioPrompter(args.url, args.timeout)
    print(f"Benchmarking {len(args.temps)} temperatures × {args.trials} trials")
    print(f"Concept: {args.concept!r}\n")

    results = _bench(args.temps, args.trials, prompter, args.concept)
    _print_table(results)
    _plot(results, args.trials, args.output)


if __name__ == "__main__":
    main()
