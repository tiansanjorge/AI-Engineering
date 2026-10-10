"""Calibra al evaluador (LLM-juez) contra puntajes humanos.

Lee eval/judge_calibration.json (30 items con `human_score` escrito ANTES de correr el juez),
resuelve el contexto de cada item desde el corpus, corre el juez y mide el acuerdo: correlacion de
Spearman, error absoluto medio, sesgo, acuerdo binario (bueno >= 7) y los errores mas peligrosos
(el juez da por buena una respuesta mala). Se reporta por separado el split `tune` (sobre el que se
puede ajustar el prompt) y el `test` (que no se mira al ajustar).

Uso (desde modulo-3/):  python scripts/calibrate_judge.py --label v1
"""

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import MODULE_ROOT
from src.evaluation import judge_agreement
from src.evaluator import JUDGE_MODEL, ContextChunk, judge_response
from src.ingestion import load_domain

CALIBRATION = MODULE_ROOT / "eval" / "judge_calibration.json"
RESULTS = MODULE_ROOT / "eval" / "judge_calibration_runs"
HISTORY = MODULE_ROOT / "eval" / "judge_calibration_history.csv"
FIELDS = ["label", "judge_model", "timestamp", "split", "n", "spearman", "mae", "bias",
          "within_1", "within_2", "binary_agreement", "false_good", "false_bad"]  # fmt: skip


def resolve_context(item: dict) -> list[ContextChunk]:
    chunks = [
        c
        for c in load_domain(item["domain"])
        if c.metadata["section"] in item["context_sections"]
    ]
    cited = item["status"] == "answered"
    return [ContextChunk(c.metadata["chunk_id"], c.page_content, cited) for c in chunks]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calibra al juez contra puntajes humanos"
    )
    parser.add_argument("--label", required=True)
    args = parser.parse_args()

    items = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    rows = []
    for item in items:
        verdict = judge_response(
            item["question"], item["answer"], item["status"], resolve_context(item)
        )
        rows.append(
            {**item, "judge_score": verdict.score, "judge": verdict.model_dump()}
        )
        flag = "" if abs(verdict.score - item["human_score"]) <= 1 else "  <-- difiere"
        print(f"{item['id']} [{item['split']:4}] {item['kind']:20} humano={item['human_score']:2} "
              f"juez={verdict.score:2} (rel {verdict.relevance} comp {verdict.completeness} "
              f"exac {verdict.accuracy}){flag}")  # fmt: skip

    summaries = {"all": rows, "tune": [r for r in rows if r["split"] == "tune"],
                 "test": [r for r in rows if r["split"] == "test"]}  # fmt: skip
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"{args.label}.json").write_text(
        json.dumps({"label": args.label, "judge_model": JUDGE_MODEL, "items": rows},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )  # fmt: skip
    new_file = not HISTORY.exists()
    with HISTORY.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        for split, subset in summaries.items():
            metrics = judge_agreement(
                [r["human_score"] for r in subset], [r["judge_score"] for r in subset]
            )
            writer.writerow({"label": args.label, "judge_model": JUDGE_MODEL, "split": split,
                             "timestamp": datetime.now(UTC).isoformat(), **metrics})  # fmt: skip
            print(f"\n[{split:4}] " + "  ".join(f"{k}={v}" for k, v in metrics.items()))

    print("\nPeores desacuerdos:")
    for r in sorted(rows, key=lambda r: -abs(r["judge_score"] - r["human_score"]))[:5]:
        d = r["judge"]
        print(f"  {r['id']} humano={r['human_score']} juez={r['judge_score']} :: {r['human_note']}\n"
              f"     juez dice: {d['reason']}")  # fmt: skip


if __name__ == "__main__":
    main()
