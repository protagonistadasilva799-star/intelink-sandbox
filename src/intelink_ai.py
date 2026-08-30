#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interlink AI: núcleo local de IA do ecossistema criado pelo usuário.
Usa modelos treinados localmente e mantém compatibilidade com os comandos Intelink.
Sem API externa obrigatória e sem dependências externas.
"""
import ast, json, re, sys, time
from pathlib import Path
from intelink_modelo_real import AttentionLanguageModel, CodeMind, Mission, ROOT, read_corpus, weight_path

MODEL_NAME = "Interlink AI"
AUTHOR = "Samuel"

class IntelinkAI:
    def __init__(self):
        self.model = AttentionLanguageModel.load() if weight_path().exists() else None
        self.code = CodeMind()
        self.context = []
        self.memory = ROOT / "ia_memoria.json"
        try: self.learned = json.loads(self.memory.read_text(encoding="utf-8"))
        except Exception: self.learned = []
    def save(self):
        ROOT.mkdir(parents=True, exist_ok=True)
        self.memory.write_text(json.dumps(self.learned[-1000:], ensure_ascii=False, indent=2), encoding="utf-8")
    def learn(self, text, label="experiencia"):
        self.learned.append({"tipo":label,"texto":str(text),"tempo":time.time()}); self.save()
        return {"aprendido":True,"total":len(self.learned)}
    def retrieve(self, query, limit=6):
        terms=set(re.findall(r"\w+",str(query).lower()))
        ranked=sorted(self.learned,key=lambda x:len(terms & set(re.findall(r"\w+",x["texto"].lower()))),reverse=True)
        return [x["texto"] for x in ranked[:limit]]
    def generate(self, prompt, length=320):
        if not self.model: return {"erro":"pesos ausentes; treine o modelo primeiro"}
        context="\n".join(self.retrieve(prompt))
        seed=(context+"\n"+str(prompt)).strip()[-500:]
        text=self.model.generate(seed,length=length)
        self.learn(text,"geracao")
        return {"texto":text,"modelo":MODEL_NAME,"desenvolvido_por":AUTHOR,"contexto_recuperado":bool(context)}
    def analyze(self, text):
        s=str(text); words=re.findall(r"\w+",s,re.UNICODE); lines=s.splitlines()
        result={"caracteres":len(s),"palavras":len(words),"linhas":len(lines) or 1,"codigo_python":("def " in s or "import " in s),"conceitos":sorted(set(words),key=words.index)[:30]}
        self.learn(json.dumps(result,ensure_ascii=False),"analise")
        return result
    def create(self, objective):
        code=self.code.make(objective); evaluation=self.code.evaluate(code); self.learn(objective,"objetivo_criativo")
        return {"objetivo":objective,"codigo":code,"avaliacao":evaluation}
    def mission(self, objective):
        result=Mission(self.model).run(objective,cycles=6); self.learn(json.dumps(result,ensure_ascii=False),"missao")
        return result
    def train(self, corpus=None, steps=5000):
        text=read_corpus(corpus,max_chars=500000); model=AttentionLanguageModel(text,context=8,dim=24); history=model.train(text,steps=steps); model.save(); self.model=model
        return {"treinado":True,"caracteres":len(text),"vocabulario":len(model.chars),"passos":steps,"historico":history[-5:]}

def main():
    ai=IntelinkAI()
    if len(sys.argv)>=2 and sys.argv[1]=="--treinar": print(json.dumps(ai.train(sys.argv[2] if len(sys.argv)>2 else None,int(sys.argv[3]) if len(sys.argv)>3 else 5000),ensure_ascii=False,indent=2)); return
    if len(sys.argv)>=3 and sys.argv[1]=="--criar": print(json.dumps(ai.create(" ".join(sys.argv[2:])),ensure_ascii=False,indent=2)); return
    if len(sys.argv)>=3 and sys.argv[1]=="--analisar": print(json.dumps(ai.analyze(" ".join(sys.argv[2:])),ensure_ascii=False,indent=2)); return
    if len(sys.argv)>=3 and sys.argv[1]=="--missao": print(json.dumps(ai.mission(" ".join(sys.argv[2:])),ensure_ascii=False,indent=2)); return
    if len(sys.argv)>=3 and sys.argv[1]=="--gerar": print(json.dumps(ai.generate(" ".join(sys.argv[2:])),ensure_ascii=False,indent=2)); return
    if len(sys.argv)>=3 and sys.argv[1]=="--aprender": print(json.dumps(ai.learn(" ".join(sys.argv[2:])),ensure_ascii=False,indent=2)); return
    print(f"{MODEL_NAME} — desenvolvido por {AUTHOR} | --treinar CORPUS PASSOS | --gerar TEXTO | --criar OBJETIVO | --analisar TEXTO | --missao OBJETIVO | --aprender FATO")

if __name__=="__main__": main()
