"""Generate the algorithm case's figure from its accepted summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from record import ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    rows = json.loads((ROOT / config["output_dir"] / "summary.json").read_text())["rows"]
    figure_path = ROOT / config["figure_path"]
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=config["plot"]["figsize"])
    ax.plot([row["size"] for row in rows], [row["speedup"] for row in rows], marker="o")
    ax.axhline(1, color="gray", linewidth=1)
    ax.set(xlabel="Number of values", ylabel="Linear / set time", title="Membership lookup speedup")
    fig.tight_layout()
    fig.savefig(figure_path, dpi=config["plot"]["dpi"])
    plt.close(fig)
    print(figure_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
