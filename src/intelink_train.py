#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Treinamento reproduzível do modelo Intelink usando somente código Intelink."""
import argparse
import json
import random
import shutil
from pathlib import Path

from intelink_modelo_real import AttentionLanguageModel, weight_path
from intelink_corpus import collect, build_text

VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = Path.home() / ".intelink_agent"
EXTENSIONS = {".py", ".md", ".txt", ".json", ".ilm", ".sh"}


def build_training_corpus(root, max_chars):
    records = collect(root)
    text = build_text(records)[:max_chars]
    return text, len(records)


def main():
    ap = argparse.ArgumentParser(prog="intelink-train", description="Treina o modelo Intelink do zero com o código Intelink")
    ap.add_argument("--raiz", default=str(ROOT), help="raiz do sandbox Intelink")
    ap.add_argument("--saida", default=str(DEFAULT_OUT), help="diretório de pesos e métricas")
    ap.add_argument("--passos", type=int, default=1200, help="passos de treinamento")
    ap.add_argument("--max-caracteres", type=int, default=180000)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--versao", "-v", action="store_true")
    args = ap.parse_args()
    if args.versao:
        print(VERSION)
        return
    random.seed(args.seed)
    root, out = Path(args.raiz).resolve(), Path(args.saida).expanduser().resolve()
    corpus, files = build_training_corpus(root, args.max_caracteres)
    if len(corpus) < 300:
        raise SystemExit("corpus Intelink insuficiente")
    model = AttentionLanguageModel(corpus, context=8, dim=24, seed=args.seed)
    log = model.train(corpus, steps=max(1, args.passos), batch=4, lr=.025, checkpoint=max(1, args.passos // 4))
    out.mkdir(parents=True, exist_ok=True)
    generated_weights = weight_path()
    target_weights = out / "intelink_pesos_treinados.py"
    if generated_weights.exists() and generated_weights.resolve() != target_weights.resolve():
        shutil.copy2(generated_weights, target_weights)
    metrics = {"modelo": "Interlink AI", "arquitetura": "IntelinkAttention", "versao": VERSION, "origem": "somente código Intelink", "raiz": str(root), "arquivos": files, "caracteres": len(corpus), "vocabulario": len(model.chars), "passos": args.passos, "seed": args.seed, "historico": log}
    (out / "intelink_treino_metricas.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
