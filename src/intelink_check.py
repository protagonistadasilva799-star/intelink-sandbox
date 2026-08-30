#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Intelink Check: diagnóstico local e seguro do ambiente Intelink.

A ferramenta apenas inspeciona arquivos, versões e executáveis disponíveis.
Ela não instala pacotes, não conecta à rede e não executa comandos externos.
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

VERSION = "0.1.0"


def check_file(root, relative):
    path = root / relative
    return {"item": relative, "ok": path.is_file(), "detalhe": str(path) if path.is_file() else "arquivo ausente"}


def check_command(name):
    found = shutil.which(name)
    return {"item": name, "ok": bool(found), "detalhe": found or "não encontrado"}


def diagnose(root=None):
    root = Path(root or Path(__file__).resolve().parents[1]).resolve()
    files = ["README.md", "src/intelink_runtime.py"]
    optional_files = [item for item in ("src/intelink_ai.py", "src/intelink_model_zoo.py") if (root / item).exists()]
    commands = ["python3", "ollama", "llama-cli"]
    checks = [check_file(root, item) for item in files]
    checks += [{**check_file(root, item), "opcional": True} for item in optional_files]
    checks += [{**check_command(item), "opcional": item != "python3"} for item in commands]
    python_ok = sys.version_info >= (3, 8)
    checks.append({"item": "python >= 3.8", "ok": python_ok, "detalhe": sys.version.split()[0]})
    required = [item for item in checks if not item.get("opcional")]
    passed = sum(1 for item in checks if item["ok"])
    return {
        "produto": "Intelink Check",
        "versao": VERSION,
        "ambiente": "termux" if os.environ.get("PREFIX") else "linux/sandbox",
        "raiz": str(root),
        "resumo": {"aprovados": passed, "total": len(checks), "obrigatorios_aprovados": sum(1 for item in required if item["ok"]), "obrigatorios": len(required), "status": "ok" if all(item["ok"] for item in required) else "revisao_necessaria"},
        "verificacoes": checks,
    }


def main():
    parser = argparse.ArgumentParser(prog="intelink-check", description="Diagnóstico seguro do ambiente Intelink")
    parser.add_argument("--root", help="raiz do projeto a inspecionar")
    parser.add_argument("--json", action="store_true", help="imprime relatório JSON")
    parser.add_argument("--versao", "-v", action="store_true", help="imprime a versão")
    args = parser.parse_args()
    if args.versao:
        print(VERSION)
        return
    report = diagnose(args.root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    print(f"Intelink Check {report['versao']}")
    print(f"Ambiente: {report['ambiente']} | Raiz: {report['raiz']}")
    for item in report["verificacoes"]:
        mark = "OK" if item["ok"] else "REVISAR"
        print(f"[{mark}] {item['item']}: {item['detalhe']}")
    summary = report["resumo"]
    print(f"Resultado: {summary['aprovados']}/{summary['total']} verificações aprovadas — {summary['status']}")
    raise SystemExit(0 if summary["status"] == "ok" else 1)


if __name__ == "__main__":
    main()
