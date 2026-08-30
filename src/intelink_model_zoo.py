#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Intelink Model Zoo: modelos leves e especializados, sem dependências externas."""
import argparse, json, math, re, sys
from pathlib import Path

MODELS = {
    "intent": ["saudacao", "criar", "analisar", "executar", "aprender", "ajuda"],
    "guard": ["seguro", "revisao", "bloqueado"],
    "topic": ["programacao", "ia", "termux", "documento", "geral"],
    "planner": ["ler", "planejar", "criar", "testar", "revisar", "finalizar"],
}

def tokens(text):
    return re.findall(r"[a-záéíóúâêôãõç0-9_]+", text.lower())

def features(text, size=256):
    vec=[0.0]*size
    ts=tokens(text)
    for token in ts:
        for n in (1,2):
            grams=[token[i:i+n] for i in range(max(1,len(token)-n+1))]
            for gram in grams:
                h=0
                for ch in gram: h=(h*31+ord(ch))%size
                vec[h]+=1.0
    norm=math.sqrt(sum(x*x for x in vec)) or 1.0
    return [x/norm for x in vec]

def softmax(values):
    m=max(values); ex=[math.exp(min(40,x-m)) for x in values]; s=sum(ex) or 1.0
    return [x/s for x in ex]

class LinearModel:
    def __init__(self, name, labels, size=256):
        self.name=name; self.labels=labels; self.size=size
        self.weights=[[0.0]*size for _ in labels]; self.bias=[0.0]*len(labels); self.examples=0
    def predict(self,text):
        x=features(text,self.size); scores=[sum(w*v for w,v in zip(row,x))+b for row,b in zip(self.weights,self.bias)]
        p=softmax(scores); i=max(range(len(p)),key=p.__getitem__)
        return {"label":self.labels[i],"confidence":round(p[i],6),"scores":{l:round(v,6) for l,v in zip(self.labels,p)}}
    def train(self, rows, epochs=20, lr=0.12):
        data=[(features(r["text"],self.size),self.labels.index(r["label"])) for r in rows if r.get("label") in self.labels]
        if not data: raise ValueError("nenhum exemplo compatível")
        for _ in range(epochs):
            for x,target in data:
                scores=[sum(w*v for w,v in zip(row,x))+b for row,b in zip(self.weights,self.bias)]
                p=softmax(scores)
                for k in range(len(self.labels)):
                    grad=p[k]-(1.0 if k==target else 0.0)
                    for j,v in enumerate(x): self.weights[k][j]-=lr*grad*v
                    self.bias[k]-=lr*grad
        self.examples += len(data)*epochs
    def evaluate(self, rows):
        usable=[r for r in rows if r.get("label") in self.labels]
        good=sum(self.predict(r["text"])["label"]==r["label"] for r in usable)
        return {"modelo":self.name,"exemplos":len(usable),"acuracia":round(good/len(usable),6) if usable else 0.0}
    def save(self,path):
        Path(path).write_text("# pesos Intelink Model Zoo\nMODEL = "+repr({"name":self.name,"labels":self.labels,"size":self.size,"weights":self.weights,"bias":self.bias,"examples":self.examples})+"\n",encoding="utf-8")
    @classmethod
    def load(cls,path):
        ns={}; exec(Path(path).read_text(encoding="utf-8"),{"__builtins__":{}},ns)
        d=ns["MODEL"]; m=cls(d["name"],d["labels"],d["size"]);m.weights=d["weights"];m.bias=d["bias"];m.examples=d.get("examples",0);return m

def seed_data():
    return {
      "intent":[
        {"text":"olá intelink", "label":"saudacao"},{"text":"preciso de ajuda", "label":"ajuda"},
        {"text":"crie um programa python", "label":"criar"},{"text":"gerar um arquivo novo", "label":"criar"},
        {"text":"analise este código", "label":"analisar"},{"text":"verifique o documento", "label":"analisar"},
        {"text":"execute pwd no termux", "label":"executar"},{"text":"rode este comando", "label":"executar"},
        {"text":"aprenda este texto", "label":"aprender"}
      ],
      "guard":[
        {"text":"pwd", "label":"seguro"},{"text":"echo olá", "label":"seguro"},{"text":"python teste.py", "label":"revisao"},
        {"text":"rm -rf /", "label":"bloqueado"},{"text":"dd if=/dev/zero of=/dev/sda", "label":"bloqueado"}
      ],
      "topic":[
        {"text":"como criar uma função python", "label":"programacao"},{"text":"rede neural e treinamento", "label":"ia"},
        {"text":"instalar pacote no termux", "label":"termux"},{"text":"ler livro e documento", "label":"documento"},
        {"text":"uma pergunta geral", "label":"geral"}
      ],
      "planner":[
        {"text":"consultar documentação local", "label":"ler"},{"text":"dividir objetivo em tarefas", "label":"planejar"},
        {"text":"escrever a solução", "label":"criar"},{"text":"rodar verificações", "label":"testar"},
        {"text":"corrigir falhas encontradas", "label":"revisar"},{"text":"entregar resultado final", "label":"finalizar"}
      ]
    }

def train_all(outdir, data_path=None, epochs=40):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True);data=seed_data()
    if data_path:
        for line in Path(data_path).read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            row=json.loads(line);data.setdefault(row["model"],[]).append({"text":row["text"],"label":row["label"]})
    reports=[]
    for name,labels in MODELS.items():
        m=LinearModel(name,labels);m.train(data.get(name,[]),epochs=epochs);m.save(out/f"intelink_{name}_pesos.py");reports.append(m.evaluate(data.get(name,[])))
    (out/"metricas.json").write_text(json.dumps({"modelos":reports,"epocas":epochs},ensure_ascii=False,indent=2),encoding="utf-8");return reports

def main():
    ap=argparse.ArgumentParser(prog="intelink-zoo");sub=ap.add_subparsers(dest="cmd")
    p=sub.add_parser("treinar");p.add_argument("--saida",default=".intelink_zoo");p.add_argument("--dados");p.add_argument("--epocas",type=int,default=40)
    p=sub.add_parser("prever");p.add_argument("modelo");p.add_argument("texto",nargs="+")
    p=sub.add_parser("avaliar");p.add_argument("--modelos",default=".intelink_zoo")
    a=ap.parse_args()
    if a.cmd=="treinar": print(json.dumps(train_all(a.saida,a.dados,a.epocas),ensure_ascii=False,indent=2));return
    if a.cmd=="prever": print(json.dumps(LinearModel.load(a.modelo).predict(" ".join(a.texto)),ensure_ascii=False,indent=2));return
    if a.cmd=="avaliar": print(Path(a.modelos,"metricas.json").read_text(encoding="utf-8"));return
    ap.print_help()
if __name__=="__main__": main()
