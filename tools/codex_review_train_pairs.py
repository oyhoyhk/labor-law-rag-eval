"""Third-opinion audit of the fine-tuning pair sample with local Codex (gpt-6-astra), same prompt as the Opus audit.

Usage: uv run python tools/codex_review_train_pairs.py [--version v1|v2] [--ids t01,t02]
Output: data/train/review_codex_<version>.json  {pair id: {verdict, reason}}
"""

import argparse
import json
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from opus_review_train_pairs import build_prompt

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gpt-6-astra"
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["verdict", "reason"],
          "properties": {"verdict": {"type": "string", "enum": ["ok", "bad", "unsure"]}, "reason": {"type": "string"}}}
SCHEMA_V2 = {"type": "object", "additionalProperties": False, "required": ["verdict", "answers", "distinct", "reason"],
             "properties": {"verdict": {"type": "string", "enum": ["ok", "bad", "unsure"]}, "answers": {"type": "boolean"},
                            "distinct": {"type": "boolean"}, "reason": {"type": "string"}}}


def judge(it: dict, version: str = "v1") -> tuple[str, dict]:
    prompt = "파일을 읽거나 명령을 실행하지 말고, 아래 내용만 보고 판정하세요.\n\n" + build_prompt(it, version)
    with tempfile.TemporaryDirectory() as d:  # empty working dir: no repo files or AGENTS.md from the project
        schema, out = Path(d) / "schema.json", Path(d) / "out.json"
        schema.write_text(json.dumps(SCHEMA_V2 if version == "v2" else SCHEMA))
        cmd = ["codex", "exec", "-m", MODEL, "-s", "read-only", "--skip-git-repo-check", "--ephemeral", "-C", d,
               "--output-schema", str(schema), "-o", str(out), "-"]
        for _ in range(2):
            proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=600)
            try:
                res = json.loads(out.read_text())
                if res.get("verdict") in ("ok", "bad", "unsure"):
                    return it["id"], {k: res[k] for k in ("verdict", "answers", "distinct", "reason") if k in res}
            except (OSError, json.JSONDecodeError):
                pass
    return it["id"], {"verdict": None, "reason": f"판정 실패: {proc.stderr[-200:]}"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="")
    ap.add_argument("--version", default="v1", choices=["v1", "v2"])
    args = ap.parse_args()
    items = json.loads((ROOT / "data/train/review_sample_v1.json").read_text())
    if args.ids:
        items = [i for i in items if i["key"] in args.ids.split(",")]
    with ThreadPoolExecutor(4) as ex:
        verdicts = dict(ex.map(lambda it: judge(it, args.version), items))
    if args.ids:
        print(json.dumps(verdicts, ensure_ascii=False, indent=1))
        return
    ver = subprocess.run(["codex", "--version"], capture_output=True, text=True).stdout.strip()
    (ROOT / f"data/train/review_codex_{args.version}.json").write_text(json.dumps(
        {"rater": MODEL, "prompt": args.version, "cli": ver, "at": datetime.now().isoformat(timespec="seconds"), "verdicts": verdicts},
        ensure_ascii=False, indent=1))
    from collections import Counter
    print(Counter((it["source"], verdicts[it["id"]]["verdict"]) for it in items))


if __name__ == "__main__":
    main()
