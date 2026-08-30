#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Intelink Stable — camada de estabilidade para modelos pequenos.

A camada não promete eliminar todos os erros. Ela reduz desvios ao exigir
contexto recuperado, medir relevância lexical, bloquear repetições e responder
com incerteza quando não há evidência suficiente.
"""
import json, math, re, sys, time
from pathlib import Path
from intelink_ai import IntelinkAI

ROOT = Path.home() / ".intelink_agent"
STATE = ROOT / "stable_state.json"
STOP = {"a","o","e","de","da","do","das","dos","um","uma","para","por","que","com","sem","em","no","na","os","as","é","se","eu","você","sobre"}

class IntelinkStable:
    def __init__(self, threshold=.18, max_context=4):
        self.ai=IntelinkAI(); self.threshold=threshold; self.max_context=max_context
        self.state=self.load(); self.last=[]
    def load(self):
        try: return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception: return {"perguntas":0,"abstencoes":0,"verificadas":0}
    def save(self):
        ROOT.mkdir(parents=True,exist_ok=True); STATE.write_text(json.dumps(self.state,ensure_ascii=False,indent=2),encoding="utf-8")
    def terms(self,text): return {x for x in re.findall(r"[\wÀ-ÿ]+",str(text).lower()) if len(x)>2 and x not in STOP}
    def score(self,query,doc):
        q,d=self.terms(query),self.terms(doc)
        if not q or not d:return 0.0
        return len(q&d)/math.sqrt(len(q)*len(d))
    def add_knowledge(self,text,source="local"):
        item={"texto":str(text),"fonte":source,"tempo":time.time()}
        data=self.state.setdefault("conhecimento",[]); data.append(item); self.state["conhecimento"]=data[-5000:]; self.save()
        return {"adicionado":True,"fonte":source,"total":len(data)}
    def retrieve(self,query):
        docs=list(self.state.get("conhecimento",[]))
        docs += [{"texto":x,"fonte":"memoria"} for x in self.ai.retrieve(query,limit=12)]
        ranked=sorted(((self.score(query,d["texto"]),d) for d in docs),key=lambda x:x[0],reverse=True)
        return [(round(s,3),d) for s,d in ranked[:self.max_context] if s>=self.threshold]
    def clean(self,text):
        lines=[]; seen=set()
        for line in re.split(r"(?<=[.!?])\s+|\n+",str(text).strip()):
            line=re.sub(r"\s+"," ",line).strip(); key=line.lower()
            if line and key not in seen: lines.append(line); seen.add(key)
        return " ".join(lines)
    def verify(self,query,answer,evidence):
        q=self.terms(query); a=self.terms(answer); e=set().union(*(self.terms(x[1]["texto"]) for x in evidence)) if evidence else set()
        overlap=len((a& (q|e)))/max(1,len(a)); repeated=len(a)-len(set(a));
        flags=[]
        if repeated>max(4,len(a)//3): flags.append("repetição")
        if evidence and overlap<.08: flags.append("baixa_ancoragem")
        return {"aprovada":not flags,"ancoragem":round(overlap,3),"sinais":flags}
    def answer(self,query):
        self.state["perguntas"]=self.state.get("perguntas",0)+1
        evidence=self.retrieve(query)
        if not evidence:
            self.state["abstencoes"]=self.state.get("abstencoes",0)+1; self.save()
            return {"resposta":"Não encontrei evidência suficiente na minha base local para responder com segurança.","confianca":0.0,"fontes":[],"abstencao":True}
        context="\n".join(f"[{d['fonte']}] {d['texto']}" for _,d in evidence)
        result=self.ai.generate("Use somente o contexto abaixo. Se ele não responder à pergunta, diga que não há evidência suficiente.\nCONTEXTO:\n"+context+"\nPERGUNTA: "+query,length=280)
        text=self.clean(result.get("texto","")); check=self.verify(query,text,evidence)
        if not check["aprovada"]:
            self.state["abstencoes"]=self.state.get("abstencoes",0)+1; text="A resposta gerada não passou pela verificação de estabilidade; não vou inventar uma conclusão."
        else:self.state["verificadas"]=self.state.get("verificadas",0)+1
        self.save(); return {"resposta":text,"confianca":round(sum(x[0] for x in evidence)/len(evidence),3),"fontes":[d["fonte"] for _,d in evidence],"verificacao":check,"abstencao":not check["aprovada"]}

def main():
    stable=IntelinkStable()
    if len(sys.argv)>=3 and sys.argv[1]=="--conhecer": print(json.dumps(stable.add_knowledge(" ".join(sys.argv[2:]),"linha_de_comando"),ensure_ascii=False,indent=2)); return
    if len(sys.argv)>=3 and sys.argv[1]=="--responder": print(json.dumps(stable.answer(" ".join(sys.argv[2:])),ensure_ascii=False,indent=2)); return
    print("Intelink Stable | --conhecer TEXTO | --responder PERGUNTA")
if __name__=="__main__": main()
