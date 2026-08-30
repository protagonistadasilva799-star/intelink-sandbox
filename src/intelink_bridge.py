#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ponte oficial Intelink <-> Python para Termux.

Formato de arquivo .imx:
  linguagem intelink
  x = 7;
  imprimir(x);
  fim
  linguagem python
  resultado = x * 6
  print(resultado)
  fim

Arquivos são confiáveis por definição: blocos Python têm os mesmos poderes do
Python executado pelo usuário. A ponte apenas controla a alternância e o estado.
"""
import contextlib, io, json, runpy, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from intelink_runtime import Engine, IntelinkError

class IntelinkPythonBridge:
    def __init__(self):
        self.state = {}
        self.engine = Engine()
        self.engine.env = self.state
        self.python_globals = {"__name__": "__intelink_python__", "intelink_state": self.state}
    def run_intelink(self, source):
        self.engine.env = self.state
        self.engine.run(source)
    def run_python(self, source):
        self.python_globals.update(self.state)
        self.python_globals.update({"intelink_state": self.state})
        exec(compile(source, "<intelink-python>", "exec"), self.python_globals, self.python_globals)
        for key, value in self.python_globals.items():
            if not key.startswith("__") and key not in {"intelink_state"}: self.state[key] = value
    def run_file(self, path):
        blocks=[]; current=None; lines=[]
        for number, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
            line=raw.strip(); low=line.lower()
            if low.startswith("linguagem "):
                if current is not None: raise IntelinkError("bloco sem fim na linha " + str(number))
                current=low.split(None,1)[1]; lines=[]
            elif low == "fim":
                if current not in {"intelink","python"}: raise IntelinkError("linguagem inválida")
                blocks.append((current,"\n".join(lines))); current=None; lines=[]
            elif current is not None: lines.append(raw)
            elif line and not line.startswith("#"): raise IntelinkError("conteúdo fora de bloco na linha " + str(number))
        if current is not None: raise IntelinkError("último bloco não terminou com fim")
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            for kind, source in blocks:
                if kind == "intelink": self.run_intelink(source)
                else: self.run_python(source)
        return {"blocos":len(blocks),"estado":self.state,"saida":output.getvalue()}

def main():
    if len(sys.argv) != 2 or sys.argv[1] in {"-h","--ajuda"}:
        print("Uso: intelink-mix arquivo.imx"); print("Blocos: linguagem intelink ... fim | linguagem python ... fim"); return
    print(json.dumps(IntelinkPythonBridge().run_file(sys.argv[1]), ensure_ascii=False, indent=2, default=str))

if __name__ == "__main__": main()
