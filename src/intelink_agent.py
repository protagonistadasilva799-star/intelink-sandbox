#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Intelink Agent: agente local construído sobre os componentes Intelink.

O agente não é um LLM geral. Ele combina recuperação lexical, memória persistente,
planejamento explícito, classificadores opcionais e o modelo local Intelink.
"""
import argparse
import hashlib
import json
import re
import time
from pathlib import Path

from intelink_ai import IntelinkAI

VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parents[1]
STATE = Path.home() / ".intelink_agent" / "agent_state.json"


class IntelinkAgent:
    def __init__(self, root=None):
        self.root = Path(root or ROOT).resolve()
        self.ai = IntelinkAI()
        self.state = self._load()
        self.index = self._build_index()

    def _load(self):
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"memoria": [], "perguntas": 0, "respostas": 0}

    def _save(self):
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

    def _build_index(self):
        records = []
        for path in sorted(self.root.rglob("*")):
            if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if path.suffix.lower() not in {".py", ".md", ".txt", ".json", ".ilm"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            lines = text.splitlines()
            for start in range(0, len(lines), 80):
                chunk = "\n".join(lines[start:start + 80]).strip()
                if len(chunk) < 20:
                    continue
                records.append({"fonte": str(path.relative_to(self.root)), "inicio": start + 1, "texto": chunk})
        return records

    @staticmethod
    def _terms(text):
        return {x for x in re.findall(r"[\wÀ-ÿ]+", str(text).lower()) if len(x) > 2}

    def retrieve(self, query, limit=5):
        wanted = self._terms(query)
        if not wanted:
            return []
        ranked = []
        for doc in self.index:
            terms = self._terms(doc["texto"])
            overlap = len(wanted & terms)
            if overlap:
                score = overlap / max(1, len(wanted))
                ranked.append((score, doc))
        ranked.sort(key=lambda item: (-item[0], item[1]["fonte"], item[1]["inicio"]))
        return [{**doc, "relevancia": round(score, 3)} for score, doc in ranked[:limit]]

    def remember(self, text, kind="aprendizado"):
        item = {"tipo": kind, "texto": str(text), "tempo": time.time()}
        self.state.setdefault("memoria", []).append(item)
        self.state["memoria"] = self.state["memoria"][-1000:]
        self._save()
        return item

    def classify(self, query):
        terms = self._terms(query)
        if terms & {"criar", "programar", "código", "codigo", "projeto"}:
            return "criar"
        if terms & {"analisar", "explicar", "entender", "verificar"}:
            return "analisar"
        if terms & {"lembrar", "aprender", "guardar"}:
            return "aprender"
        if terms & {"executar", "rodar", "comando"}:
            return "executar"
        return "conversar"

    def plan(self, query, intent):
        steps = {
            "criar": ["entender objetivo", "consultar componentes Intelink", "propor implementação", "verificar riscos"],
            "analisar": ["localizar evidências", "comparar trechos", "resumir comportamento", "apontar incertezas"],
            "aprender": ["normalizar informação", "registrar na memória", "confirmar armazenamento"],
            "executar": ["identificar comando", "verificar permissão", "pedir confirmação", "registrar resultado"],
            "conversar": ["recuperar contexto", "formular resposta", "indicar limites"],
        }
        return {"objetivo": query, "intencao": intent, "passos": steps[intent]}

    def answer(self, query, generate=True):
        self.state["perguntas"] = self.state.get("perguntas", 0) + 1
        intent = self.classify(query)
        plan = self.plan(query, intent)
        evidence = self.retrieve(query)
        memory = [m["texto"] for m in self.state.get("memoria", []) if self._terms(query) & self._terms(m["texto"])] [-5:]
        context = "\n".join(f"[{x['fonte']}:{x['inicio']}] {x['texto']}" for x in evidence)
        if memory:
            context += "\n[MEMORIA] " + "\n[MEMORIA] ".join(memory)
        if generate and self.ai.model and context:
            prompt = ("Você é o Intelink Agent. Responda em português usando somente o contexto. "
                      "Se o contexto não bastar, declare a incerteza. Não invente APIs.\n"
                      f"PLANO: {json.dumps(plan, ensure_ascii=False)}\nCONTEXTO:\n{context}\nPERGUNTA: {query}")
            result = self.ai.generate(prompt, length=360)
            text = result.get("texto", "")
        elif context:
            text = "Encontrei estas evidências no projeto:\n" + "\n".join(f"- {x['fonte']}:{x['inicio']} (relevância {x['relevancia']})" for x in evidence)
        else:
            text = "Não encontrei evidência suficiente no código e na memória local para responder com segurança."
        self.state["respostas"] = self.state.get("respostas", 0) + 1
        self.remember(f"pergunta: {query} | intenção: {intent}", "interação")
        return {"resposta": text.strip(), "identidade": "Interlink AI — desenvolvido por Samuel", "intencao": intent, "plano": plan, "fontes": evidence, "modelo_local": bool(self.ai.model and generate)}

    def teach(self, text):
        item = self.remember(text, "conhecimento_do_usuario")
        self.ai.learn(text, "conhecimento_do_usuario")
        return {"registrado": True, "item": item, "total_memorias": len(self.state["memoria"])}

    def create_code(self, objective):
        plan = self.plan(objective, "criar")
        result = self.ai.create(objective)
        code = result.get("codigo", "")
        try:
            compile(code, "<interlink-generated>", "exec")
            syntax = "PASS"
        except SyntaxError as exc:
            syntax = f"FAIL: linha {exc.lineno}: {exc.msg}"
        self.remember(f"código analisado para: {objective} | sintaxe: {syntax}", "programação")
        return {"identidade": "Interlink AI — desenvolvido por Samuel", "objetivo": objective, "plano_resumido": plan["passos"], "codigo": code, "validacao_sintatica": syntax, "executado": False}


def main():
    ap = argparse.ArgumentParser(prog="intelink-agent", description="Agente local baseado no ecossistema Intelink")
    ap.add_argument("--perguntar", help="faz uma pergunta sobre o código Intelink")
    ap.add_argument("--ensinar", help="registra um conhecimento na memória local")
    ap.add_argument("--criar", help="cria código e valida a sintaxe sem executá-lo")
    ap.add_argument("--sem-geracao", action="store_true", help="retorna somente evidências recuperadas")
    ap.add_argument("--json", action="store_true", help="imprime JSON")
    ap.add_argument("--versao", "-v", action="store_true")
    args = ap.parse_args()
    if args.versao:
        print(VERSION)
        return
    agent = IntelinkAgent()
    if args.ensinar:
        result = agent.teach(args.ensinar)
    elif args.criar:
        result = agent.create_code(args.criar)
    elif args.perguntar:
        result = agent.answer(args.perguntar, generate=not args.sem_geracao)
    else:
        ap.print_help()
        return
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result)


if __name__ == "__main__":
    main()
