#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Constrói o corpus de treinamento exclusivamente a partir do ecossistema Intelink."""
import argparse
import hashlib
import json
from pathlib import Path

VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parents[1]
EXTENSIONS = {".py", ".md", ".txt", ".json", ".jsonl", ".ilm", ".sh"}
EXCLUDED = {".git", "__pycache__", ".mypy_cache", ".pytest_cache"}
BLOCKED_TERMS = ("supra", "supralabs")
BLOCKED_FILES = {"MODEL_PROVENANCE.md"}


def clean_text(text):
    lines = []
    for line in text.splitlines():
        lowered = line.lower()
        if any(term in lowered for term in BLOCKED_TERMS):
            continue
        lines.append(line)
    return "\n".join(lines)


def collect(root):
    records = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or EXCLUDED.intersection(path.parts):
            continue
        if path.suffix.lower() not in EXTENSIONS:
            continue
        relative = str(path.relative_to(root))
        if relative in BLOCKED_FILES:
            continue
        text = clean_text(path.read_text(encoding="utf-8", errors="replace"))
        records.append({
            "arquivo": relative,
            "tipo": path.suffix.lower()[1:] or "sem_extensao",
            "caracteres": len(text),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "texto": text,
        })
    return records


def build_text(records):
    blocks = []
    for record in records:
        text = record["texto"]
        if record["tipo"] == "jsonl":
            dialogue = []
            for line in text.splitlines():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "mensagem" in row and "resposta" in row:
                    dialogue.append(
                        "### DIALOGO\n"
                        "[USUARIO]\n" + str(row["mensagem"]) +
                        "\n[ASSISTENTE]\n" + str(row["resposta"]) + "\n[FIM]"
                    )
            if dialogue:
                blocks.append("### INTELINK/" + record["arquivo"] + "\n" + "\n".join(dialogue))
                continue
        blocks.append(f"### INTELINK/{record['arquivo']}\n{text}")
    return "\n\n".join(blocks)


def main():
    ap = argparse.ArgumentParser(description="Constrói corpus interno do Intelink")
    ap.add_argument("--raiz", default=str(ROOT))
    ap.add_argument("--saida", default=str(Path.home() / ".intelink_agent" / "intelink_corpus.json"))
    ap.add_argument("--texto", help="salva também o corpus textual")
    ap.add_argument("--max-caracteres", type=int, default=500000)
    args = ap.parse_args()
    root = Path(args.raiz).resolve()
    records = collect(root)
    text = build_text(records)[:args.max_caracteres]
    payload = {"produto": "Intelink Corpus", "versao": VERSION, "origem": "somente código e documentação Intelink", "raiz": str(root), "arquivos": records, "total_arquivos": len(records), "total_caracteres": len(text), "corpus_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    out = Path(args.saida).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.texto:
        Path(args.texto).expanduser().write_text(text, encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("produto", "versao", "total_arquivos", "total_caracteres", "corpus_sha256")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
