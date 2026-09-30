"""Correctness gate and resumable timing for the algorithm one-shot case."""

from __future__ import annotations

import argparse
import random
import statistics
import time
from pathlib import Path

from record import ROOT, append_row, load_rows, start_run, write_json


def linear_lookup(values: list[int], queries: list[int]) -> list[bool]:
    return [query in values for query in queries]


def set_lookup(values: list[int], queries: list[int]) -> list[bool]:
    lookup = set(values)
    return [query in lookup for query in queries]


def measure(method, values: list[int], queries: list[int], warmup: int, repetitions: int) -> float:
    for _ in range(warmup):
        method(values, queries)
    samples = []
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        method(values, queries)
        samples.append((time.perf_counter_ns() - start) / 1_000_000)
    return statistics.median(samples)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config, output_dir = start_run(args.config, list(Path(__file__).parent.glob("*.py")))
    checkpoint = output_dir / "checkpoint.jsonl"
    rows = load_rows(checkpoint)
    if not config["sizes"] or any(size < 1 for size in config["sizes"]):
        raise ValueError("sizes must contain positive integers")
    if config["query_count"] < 1 or config["repetitions"] < 1 or config["warmup"] < 0:
        raise ValueError("query_count and repetitions must be positive; warmup must be nonnegative")

    for size in config["sizes"]:
        key = str(size)
        if key in rows:
            continue
        rng = random.Random(config["seed"] + size)
        values = rng.sample(range(size * 2), size)
        queries = [rng.randrange(size * 2) for _ in range(config["query_count"])]
        if linear_lookup(values, queries) != set_lookup(values, queries):
            raise AssertionError(f"methods disagree at size {size}")
        linear_ms = measure(linear_lookup, values, queries, config["warmup"], config["repetitions"])
        set_ms = measure(set_lookup, values, queries, config["warmup"], config["repetitions"])
        row = {"id": key, "size": size, "linear_ms": linear_ms, "set_ms": set_ms, "speedup": linear_ms / set_ms}
        append_row(checkpoint, row)
        rows[key] = row

    summary = output_dir / "summary.json"
    if not summary.exists():
        write_json(summary, {"rows": [rows[str(size)] for size in config["sizes"]]})
    print(summary.relative_to(ROOT))


if __name__ == "__main__":
    main()
