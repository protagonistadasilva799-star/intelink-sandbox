#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Intelink Language - runtime 0.1 para Termux/ARM32.
Linguagem própria, interpretada em Python padrão, sem dependências externas.
"""
import ast, json, math, os, re, shlex, subprocess, sys, time
from pathlib import Path

VERSION = "0.1.0"
HOME = Path(os.environ.get("INTELINK_HOME", Path.home() / ".intelink"))
MEMORY = HOME / "memory.json"

class IntelinkError(Exception): pass

class Memory:
    def __init__(self):
        HOME.mkdir(parents=True, exist_ok=True)
        try: self.data = json.loads(MEMORY.read_text(encoding="utf-8"))
        except Exception: self.data = {"facts": [], "experiences": [], "artifacts": []}
    def save(self): MEMORY.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
    def remember(self, item, kind="fact"):
        key = "facts" if kind == "fact" else "experiences"
        self.data.setdefault(key, []).append({"text": str(item), "time": time.time()}); self.data[key] = self.data[key][-500:]; self.save(); return item
    def search(self, query, limit=5):
        terms = set(re.findall(r"\w+", str(query).lower())); items = self.data.get("facts", []) + self.data.get("experiences", [])
        ranked = sorted(items, key=lambda x: len(terms & set(re.findall(r"\w+", x.get("text", "").lower()))), reverse=True)
        if not terms:
            return []
        return [x["text"] for x in ranked if terms & set(re.findall(r"\w+", x.get("text", "").lower()))][:limit]

class SafeTools:
    allowed = {"pwd","ls","dir","date","whoami","id","uname","echo","printf","cat","head","tail","wc","grep","find","python","python3","termux-battery-status","termux-clipboard-get","termux-toast","termux-vibrate"}
    blocked = {"rm","dd","mkfs","reboot","shutdown","poweroff","su","sudo","chmod","chown","mount","umount","kill","pkill","iptables","curl","wget","ssh","scp","apt","pkg","pip","pip3","git"}
    def run(self, command, confirm=True):
        try: parts = shlex.split(str(command))
        except ValueError as e: raise IntelinkError(str(e))
        if not parts: raise IntelinkError("comando vazio")
        name = os.path.basename(parts[0])
        if name in self.blocked or name not in self.allowed: raise IntelinkError("ferramenta não autorizada: " + name)
        if any(x in str(command) for x in [";","&&","||","|",">","<","`","$("]): raise IntelinkError("encadeamento bloqueado")
        if confirm and input("Autorizar Termux: " + str(command) + "? [s/N] ").strip().lower() not in {"s","sim","y","yes"}: return "cancelado"
        p = subprocess.run(parts, capture_output=True, text=True, timeout=30, cwd=str(Path.home()))
        return (p.stdout or p.stderr).strip()

class Lexer:
    pattern = re.compile(r'\s*(?:(\d+(?:\.\d+)?)|("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')|([A-Za-z_À-ÿ][\wÀ-ÿ]*)|(==|!=|<=|>=|[+\-*/%=<>{}(),;\[\].]))')
    def __init__(self, text):
        self.tokens=[]; pos=0
        while pos < len(text):
            if text[pos] == "#":
                end=text.find("\n", pos); pos=len(text) if end<0 else end; continue
            m=self.pattern.match(text,pos)
            if not m:
                if text[pos:].strip(): raise IntelinkError("símbolo inválido perto de: " + text[pos:pos+20])
                break
            number,string,word,op=m.groups(); self.tokens.append(("num",number) if number else ("str",string) if string else ("word",word) if word else (op,op)); pos=m.end()
        self.tokens.append(("EOF","EOF")); self.i=0
    def peek(self): return self.tokens[self.i]
    def take(self, kind=None):
        t=self.tokens[self.i]
        if kind and t[0] != kind: raise IntelinkError("esperado " + kind + ", recebido " + t[1])
        self.i += 1; return t
    def accept(self, kind):
        if self.peek()[0] == kind: return self.take()
        return None

class Parser:
    def __init__(self,text): self.l=Lexer(text)
    def program(self):
        out=[]
        while self.l.peek()[0] != "EOF":
            out.append(self.statement()); self.l.accept(";")
        return out
    def statement(self):
        if self.l.peek() == ("word","se"):
            self.l.take(); cond=self.expr(); self.l.take("{"); body=[]
            while self.l.peek()[0] != "}": body.append(self.statement()); self.l.accept(";")
            self.l.take("}"); return ("if",cond,body)
        if self.l.peek() == ("word","funcao"):
            self.l.take(); name=self.l.take("word")[1]; self.l.take("("); args=[]
            while self.l.peek()[0] != ")": args.append(self.l.take("word")[1]);
            
            self.l.take(")"); self.l.take("{"); body=[]
            while self.l.peek()[0] != "}": body.append(self.statement()); self.l.accept(";")
            self.l.take("}"); return ("func",name,args,body)
        if self.l.peek()[0] == "word" and self.l.tokens[self.l.i+1][0] == "=":
            name=self.l.take("word")[1]; self.l.take("="); return ("set",name,self.expr())
        if self.l.peek() == ("word","retorna"): self.l.take(); return ("return",self.expr())
        return ("expr",self.expr())
    def expr(self): return self.compare()
    def compare(self):
        x=self.term()
        while self.l.peek()[0] in {"==","!=","<",">","<=",">="}:
            op=self.l.take()[0]; x=("bin",op,x,self.term())
        return x
    def term(self):
        x=self.factor()
        while self.l.peek()[0] in {"+","-"}:
            op=self.l.take()[0]; x=("bin",op,x,self.factor())
        return x
    def factor(self):
        x=self.unary()
        while self.l.peek()[0] in {"*","/","%"}:
            op=self.l.take()[0]; x=("bin",op,x,self.unary())
        return x
    def unary(self):
        if self.l.accept("-"): return ("unary",self.unary())
        return self.atom()
    def atom(self):
        t=self.l.take()
        if t[0] == "num": return ("lit",float(t[1]) if "." in t[1] else int(t[1]))
        if t[0] == "str": return ("lit",ast.literal_eval(t[1]))
        if t[0] == "[":
            a=[]
            while self.l.peek()[0] != "]": a.append(self.expr()); self.l.accept(",")
            self.l.take("]"); return ("list",a)
        if t[0] == "word":
            if t[1] in {"verdadeiro","true"}: return ("lit",True)
            if t[1] in {"falso","false"}: return ("lit",False)
            if self.l.accept("("):
                args=[]
                while self.l.peek()[0] != ")": args.append(self.expr()); self.l.accept(",")
                self.l.take(")"); return ("call",t[1],args)
            return ("var",t[1])
        if t[0] == "(":
            x=self.expr(); self.l.take(")"); return x
        raise IntelinkError("expressão inesperada: " + t[1])

class Engine:
    def __init__(self):
        self.env={}; self.funcs={}; self.mem=Memory(); self.tools=SafeTools()
        self.builtins={"imprimir":lambda *x: print(*x), "tamanho":lambda x:len(x), "soma":lambda x:sum(x), "maximo":lambda x:max(x), "minimo":lambda x:min(x), "texto":lambda x:str(x), "numero":lambda x:float(x), "lembrar":lambda x:self.mem.remember(x), "buscar":lambda x:self.mem.search(x), "criar":self.create, "analisar":self.analyze, "executar":self.tools.run}
    def create(self, objective):
        result = "PLANO DE CRIAÇÃO\n1. entender objetivo: %s\n2. decompor em componentes\n3. produzir primeira versão\n4. testar casos normais e falhos\n5. revisar e registrar melhoria" % objective
        self.mem.remember("criação: " + str(objective), "experience"); return result
    def analyze(self, value):
        s=str(value); words=re.findall(r"\w+",s, re.UNICODE); result={"caracteres":len(s),"palavras":len(words),"linhas":s.count("\n")+1,"tem_codigo":("def " in s or "funcao " in s)}; self.mem.remember("análise: " + json.dumps(result,ensure_ascii=False),"experience"); return result
    def ev(self,n,local=None):
        local= self.env if local is None else local; k=n[0]
        if k=="lit": return n[1]
        if k=="var": return local.get(n[1],self.builtins.get(n[1],None))
        if k=="list": return [self.ev(x,local) for x in n[1]]
        if k=="unary": return -self.ev(n[1],local)
        if k=="bin":
            a,b=self.ev(n[2],local),self.ev(n[3],local); return {"+":lambda:a+b,"-":lambda:a-b,"*":lambda:a*b,"/":lambda:a/b,"%":lambda:a%b,"==":lambda:a==b,"!=":lambda:a!=b,"<":lambda:a<b,">":lambda:a>b,"<=":lambda:a<=b,">=":lambda:a>=b}[n[1]]()
        if k=="call":
            f=self.funcs.get(n[1]) or self.builtins.get(n[1])
            if not f: raise IntelinkError("função desconhecida: " + n[1])
            args=[self.ev(x,local) for x in n[2]]
            if isinstance(f,tuple):
                scope=dict(zip(f[1],args))
                try: self.exec_stmts(f[2],scope)
                except Return as r: return r.value
                return None
            return f(*args)
    def exec_stmts(self,stmts,local=None):
        local=self.env if local is None else local
        for s in stmts:
            if s[0]=="set": local[s[1]]=self.ev(s[2],local)
            elif s[0]=="expr": self.ev(s[1],local)
            elif s[0]=="return": raise Return(self.ev(s[1],local))
            elif s[0]=="if" and self.ev(s[1],local): self.exec_stmts(s[2],local)
            elif s[0]=="func": self.funcs[s[1]]=("user",s[2],s[3])
    def run(self,text):
        tree=Parser(text).program(); self.exec_stmts(tree); return self.env

class Return(Exception):
    def __init__(self,value): self.value=value

def repl():
    e=Engine(); print("Intelink Language %s | escreva código .ilk ou :ajuda" % VERSION)
    while True:
        try:
            line=input("ilk> ")
            if line in {":sair",":exit"}: break
            if line==":ajuda": print("Atribuição: x = 2; funções: funcao nome(a) { retorna a * 2 }; IA: criar(\"ideia\"), analisar(\"texto\"), lembrar(\"fato\"), buscar(\"termo\"); Termux: executar(\"pwd\")"); continue
            e.run(line); print("=>",e.env)
        except (EOFError,KeyboardInterrupt): print(); break
        except Exception as ex: print("ERRO:",ex)

def main():
    if len(sys.argv)==1: return repl()
    if sys.argv[1] in {"--version","-v"}: print(VERSION); return
    if sys.argv[1] in {"--ajuda","-h"}: print("Uso: intelink arquivo.ilk | intelink --objetivo 'texto'"); return
    if sys.argv[1] == "--objetivo": print(Engine().create(" ".join(sys.argv[2:]))); return
    p=Path(sys.argv[1]);
    if not p.exists(): raise SystemExit("arquivo não encontrado: " + str(p))
    Engine().run(p.read_text(encoding="utf-8"))

if __name__ == "__main__": main()
