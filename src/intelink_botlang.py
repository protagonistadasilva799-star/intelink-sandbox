#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Intelink BotLang 0.1 - linguagem de bots inteligentes híbridos.
Runtime em Python padrão para Termux/ARM32. Sem dependências externas.
"""
import json, os, re, shlex, subprocess, sys, time
from pathlib import Path

VERSION = "0.1.0"
ROOT = Path(os.environ.get("INTELINK_BOT_HOME", Path.home() / ".intelink_bots"))

class BotLangError(Exception): pass

class Memory:
    def __init__(self, name):
        self.file = ROOT / (re.sub(r"\W+", "_", name.lower()) + ".json")
        ROOT.mkdir(parents=True, exist_ok=True)
        try: self.data = json.loads(self.file.read_text(encoding="utf-8"))
        except Exception: self.data = {"facts": [], "events": [], "results": []}
    def save(self): self.file.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
    def remember(self, value):
        self.data.setdefault("facts", []).append({"text": str(value), "at": time.time()}); self.data["facts"] = self.data["facts"][-1000:]; self.save()
    def recall(self, term=""):
        values = self.data.get("facts", []) + self.data.get("events", []) + self.data.get("results", [])
        words = set(re.findall(r"\w+", str(term).lower()))
        ranked = sorted(values, key=lambda x: len(words & set(re.findall(r"\w+", str(x).lower()))), reverse=True)
        return [x.get("text", x) if isinstance(x, dict) else x for x in ranked[:8]]
    def event(self, event): self.data.setdefault("events", []).append({"text": event, "at": time.time()}); self.data["events"] = self.data["events"][-500:]; self.save()

class Books:
    """Biblioteca de livros/documentos sem dependências externas."""
    def __init__(self, memory): self.memory = memory
    def read(self, path):
        p = Path(path).expanduser()
        if not p.exists() or not p.is_file(): raise BotLangError("livro não encontrado: " + str(p))
        text = p.read_text(encoding="utf-8", errors="replace")[:500000]
        self.memory.remember("livro: " + p.name + " | " + text[:1200])
        return {"arquivo": str(p), "caracteres": len(text), "texto": text[:4000]}
    def search(self, term): return self.memory.recall(term)
    def create(self, path, title):
        p = Path(path).expanduser(); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# " + str(title) + "\n\nCriado pela Intelink BotLang.\n", encoding="utf-8")
        self.memory.remember("livro criado: " + str(p)); return str(p)

class Tools:
    safe = {"pwd","ls","dir","date","whoami","id","uname","echo","printf","cat","head","tail","wc","grep","find","python","python3","termux-battery-status","termux-clipboard-get","termux-toast","termux-vibrate"}
    dangerous = {"rm","dd","mkfs","reboot","shutdown","poweroff","su","sudo","chmod","chown","mount","umount","kill","pkill","iptables","curl","wget","ssh","scp","apt","pkg","pip","pip3","git"}
    def run(self, command, allowed, approve=False):
        parts = shlex.split(command)
        if not parts: raise BotLangError("comando vazio")
        name = os.path.basename(parts[0])
        if name in self.dangerous or name not in self.safe or name not in allowed: raise BotLangError("ferramenta não permitida: " + name)
        if any(x in command for x in [";","&&","||","|",">","<","`","$("]): raise BotLangError("encadeamento bloqueado")
        if approve and input("Bot solicita: " + command + " [s/N] ").lower().strip() not in {"s","sim","y","yes"}: return "ação recusada"
        p = subprocess.run(parts, capture_output=True, text=True, timeout=20, cwd=str(Path.home()))
        return (p.stdout or p.stderr).strip()

class Bot:
    def __init__(self, name, permissions):
        self.name, self.permissions = name, set(permissions); self.memory = Memory(name); self.tools = Tools(); self.books = Books(self.memory); self.events = {}
        self.variables = {"evento": "", "ultima_resposta": ""}
    def add(self, event, actions): self.events.setdefault(event, []).extend(actions)
    def render(self, text):
        def sub(m):
            key=m.group(1); return str(self.variables.get(key, self.memory.recall(key)[0] if self.memory.recall(key) else ""))
        return re.sub(r"\{\{\s*([\wÀ-ÿ]+)\s*\}\}", sub, text)
    def think(self, goal):
        context = self.memory.recall(goal)
        plan = {"objetivo": goal, "contexto": context, "passos": ["observar", "formular hipótese", "agir dentro das permissões", "verificar resultado", "aprender"]}
        self.memory.remember("pensamento: " + json.dumps(plan, ensure_ascii=False)); return plan
    def execute(self, actions, payload=""):
        self.variables["evento"] = payload; out=[]
        for kind, value in actions:
            value=self.render(value)
            try:
                if kind == "pensar": out.append(json.dumps(self.think(value), ensure_ascii=False))
                elif kind == "responder": self.variables["ultima_resposta"]=value; out.append(value)
                elif kind == "lembrar": self.memory.remember(value); out.append("memória registrada")
                elif kind == "buscar": out.append(json.dumps(self.memory.recall(value), ensure_ascii=False))
                elif kind == "executar": out.append(self.tools.run(value, self.permissions, approve=True))
                elif kind == "ler_livro": out.append(json.dumps(self.books.read(value), ensure_ascii=False))
                elif kind == "buscar_livro": out.append(json.dumps(self.books.search(value), ensure_ascii=False))
                elif kind == "criar_livro": out.append(self.books.create(value, "Livro Intelink"))
                elif kind == "analisar": out.append(json.dumps({"tamanho":len(value),"palavras":len(re.findall(r"\w+",value)),"evento":payload}, ensure_ascii=False))
                elif kind == "aguardar": time.sleep(min(float(value), 60))
            except Exception as e: out.append("falha controlada: " + str(e))
        self.memory.data.setdefault("results", []).append({"text":" | ".join(out),"at":time.time()}); self.memory.data["results"]=self.memory.data["results"][-500:]; self.memory.save(); return out
    def dispatch(self, event, payload=""):
        self.memory.event(event + ": " + payload); return self.execute(self.events.get(event, self.events.get("*", [])), payload)

class Compiler:
    action_re = re.compile(r"^(pensar|responder|lembrar|buscar|executar|ler_livro|buscar_livro|criar_livro|analisar|aguardar)\s+(.+)$", re.I)
    def compile(self, source):
        name="bot_intelink"; perms=set(); events={}; current=None; actions=[]
        for raw in source.splitlines():
            line=raw.strip()
            if not line or line.startswith("#"): continue
            m=re.match(r"bot\s+([\wÀ-ÿ-]+)", line, re.I)
            if m: name=m.group(1); continue
            m=re.match(r"permissao\s+termux\s+(.+)", line, re.I)
            if m:
                perms.update(re.findall(r"[A-Za-z0-9_-]+", m.group(1))); continue
            m=re.match(r"evento\s+([\w*À-ÿ-]+)", line, re.I)
            if m:
                if current is not None: events[current]=actions
                current=m.group(1); actions=[]; continue
            if line in {"fim", "}"}:
                if current is not None: events[current]=actions; current=None; actions=[]
                continue
            m=self.action_re.match(line)
            if m:
                value=m.group(2).strip()
                if len(value)>=2 and value[0] in "\"'" and value[-1]==value[0]: value=value[1:-1]
                actions.append((m.group(1).lower(),value)); continue
            raise BotLangError("linha desconhecida: " + line)
        if current is not None: events[current]=actions
        bot=Bot(name, perms)
        for event, acts in events.items(): bot.add(event,acts)
        return bot

def run_file(path, event=None, payload=""):
    bot=Compiler().compile(Path(path).read_text(encoding="utf-8"))
    if event: print(json.dumps({"bot":bot.name,"evento":event,"resultado":bot.dispatch(event,payload)},ensure_ascii=False,indent=2))
    else:
        print("Bot Intelink ativo: " + bot.name + " | eventos: " + ", ".join(bot.events))
        for line in sys.stdin:
            line=line.strip()
            if not line: continue
            try:
                obj=json.loads(line) if line.startswith("{") else {"evento":line,"dados":""}
                print(json.dumps({"evento":obj.get("evento","*"),"resultado":bot.dispatch(obj.get("evento","*"),str(obj.get("dados","")))},ensure_ascii=False))
            except Exception as e: print(json.dumps({"erro":str(e)},ensure_ascii=False))

def main():
    if len(sys.argv)==1: print("BotLang Intelink %s | use: intelink-bot arquivo.ilb --evento nome --dados texto"%VERSION); return
    if sys.argv[1] in {"-v","--version"}: print(VERSION); return
    if sys.argv[1] in {"-h","--ajuda"}: print("Sintaxe: bot Nome; permissao termux [pwd ls]; evento mensagem; pensar \"objetivo\"; responder \"texto\"; lembrar \"fato\"; executar \"pwd\""); return
    path=sys.argv[1]; event=None; payload=""
    if "--evento" in sys.argv: event=sys.argv[sys.argv.index("--evento")+1]
    if "--dados" in sys.argv: payload=sys.argv[sys.argv.index("--dados")+1]
    run_file(path,event,payload)

if __name__ == "__main__": main()
