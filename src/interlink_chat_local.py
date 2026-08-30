#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chat local leve do Interlink AI para modelos GGUF."""
import argparse
import json
import os
import re
import time
from pathlib import Path

from llama_cpp import Llama

NAME = "Interlink AI"
AUTHOR = "Samuel"
DEFAULT_MEMORY = Path.home() / ".interlink_ai" / "chat_memory.json"
DEFAULT_MODEL = Path(__file__).resolve().parents[1] / "models" / "original" / "interlink-ai-source.gguf"
SYSTEM = (
    f"Você é o {NAME}, desenvolvido por {AUTHOR}. "
    "Responda em português brasileiro, de forma detalhada, clara, organizada e útil. "
    "Não invente fatos. Quando não souber, diga que não sabe. "
    "Antes de responder, organize mentalmente uma solução; mostre apenas um resumo curto do plano quando solicitado."
)


def load_memory(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))[-12:]
    except (OSError, ValueError):
        return []


def save_memory(path, memory):
    p = Path(path).expanduser(); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(memory[-12:], ensure_ascii=False, indent=2), encoding="utf-8")


def compact(text, limit=900):
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text if len(text) <= limit else text[:limit] + "..."


def make_prompt(question, memory, show_plan=False):
    recent = "\n".join(f"Usuário: {x['u']}\nInterlink AI: {x['a']}" for x in memory[-4:])
    plan = "\nAntes da resposta, produza internamente um plano curto; não exponha raciocínio privado." if not show_plan else "\nInclua ao final uma seção curta chamada Plano, com no máximo 3 etapas resumidas."
    return f"### Sistema:\n{SYSTEM}{plan}\n\n### Histórico:\n{recent}\n\n### Usuário:\n{question}\n\n### Assistente:\n"


def ask(llm, question, memory, args):
    prompt = make_prompt(question, memory, args.mostrar_plano)
    result = llm(prompt, max_tokens=args.max_tokens, temperature=args.temperature, top_k=40, top_p=.9, repeat_penalty=1.18, echo=False, stop=["### Usuário:", "### Sistema:"])
    text = compact(result["choices"][0].get("text", ""), args.max_chars)
    if not text:
        text = "Não consegui produzir uma resposta textual nesta configuração."
    memory.append({"u": compact(question, 500), "a": text, "t": time.time()})
    return text


def main():
    ap = argparse.ArgumentParser(prog="interlink-chat-local")
    ap.add_argument("--modelo", default=os.environ.get("INTERLINK_MODEL", str(DEFAULT_MODEL)))
    ap.add_argument("--memoria", default=os.environ.get("INTERLINK_MEMORY", str(DEFAULT_MEMORY)))
    ap.add_argument("--perguntar")
    ap.add_argument("--mostrar-plano", action="store_true")
    ap.add_argument("--max-tokens", type=int, default=192)
    ap.add_argument("--max-chars", type=int, default=1800)
    ap.add_argument("--perfil", choices=["a10s", "sandbox"], default="a10s", help="perfil de memória e contexto")
    ap.add_argument("--temperature", type=float, default=.35)
    ap.add_argument("--n-ctx", type=int, default=512)
    ap.add_argument("--threads", type=int, default=max(1, min(4, os.cpu_count() or 2)))
    args = ap.parse_args()
    if args.perfil == "a10s":
        args.n_ctx = min(args.n_ctx, 512)
        args.max_tokens = min(args.max_tokens, 192)
        args.max_chars = min(args.max_chars, 1800)
    model = Path(args.modelo).expanduser()
    if not model.is_file():
        raise SystemExit(f"modelo não encontrado: {model}")
    llm = Llama(model_path=str(model), n_ctx=args.n_ctx, n_threads=args.threads, n_gpu_layers=0, verbose=False)
    memory = load_memory(args.memoria)
    if args.perguntar:
        print(ask(llm, args.perguntar, memory, args))
        save_memory(args.memoria, memory)
        return
    print(f"{NAME} — desenvolvido por {AUTHOR}. Digite /sair para terminar.")
    while True:
        try: question = input("Você: ").strip()
        except EOFError: break
        if question.lower() in {"/sair", "/exit", "quit"}: break
        if question:
            print(f"{NAME}: {ask(llm, question, memory, args)}")
            save_memory(args.memoria, memory)


if __name__ == "__main__":
    main()
