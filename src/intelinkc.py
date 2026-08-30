#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IntelinkC: compilador de projetos de LLM da linguagem Intelink.

Ele valida um arquivo .ilm e gera um manifesto JSON, configuração de treino e
comandos oficiais para conversão/quantização via llama.cpp. Não finge criar um
GGUF incompatível: a conversão real depende de pesos e das ferramentas do
llama.cpp instaladas no ambiente alvo.
"""
import json, os, re, shlex, sys
from pathlib import Path

VERSION="0.1.0"
class CompileError(Exception): pass

DEFAULTS={"arquitetura":"llama","dimensao":256,"camadas":4,"cabecas":4,"contexto":512,"vocabulario":32000,"passos":1000,"taxa":0.0003,"quantizacao":"Q4_K_M"}
KEYS={"arquitetura":"arquitetura","dimensao":"dimensao","camadas":"camadas","cabecas":"cabecas","contexto":"contexto","vocabulario":"vocabulario","passos":"passos","taxa":"taxa","quantizacao":"quantizacao","dados":"dados","saida":"saida"}

class Project:
    def __init__(self): self.config=dict(DEFAULTS); self.name="IntelinkModel"; self.data=[]; self.output="modelo.gguf"; self.tasks=[]
    def parse(self, source):
        in_model=False
        for n, raw in enumerate(source.splitlines(),1):
            line=raw.strip()
            if not line or line.startswith("#"): continue
            m=re.match(r"modelo\s+([\wÀ-ÿ_-]+)\s*\{?",line,re.I)
            if m: self.name=m.group(1); in_model=True; continue
            if line in {"}","fim"}: in_model=False; continue
            m=re.match(r"dados\s+(.+)",line,re.I)
            if m:
                value=m.group(1).strip().strip("\"'"); self.data.append(value); continue
            m=re.match(r"exportar\s+gguf\s+(.+?)(?:\s+([A-Za-z0-9_]+))?$",line,re.I)
            if m:
                self.output=m.group(1).strip().strip("\"'");
                if m.group(2): self.config["quantizacao"]=m.group(2).upper()
                self.tasks.append("exportar_gguf"); continue
            m=re.match(r"treinar(?:\s+(?:passos\s+)?)?(\d+)?(?:\s+taxa\s+([0-9.eE+-]+))?$",line,re.I)
            if m:
                if m.group(1): self.config["passos"]=int(m.group(1))
                if m.group(2): self.config["taxa"]=float(m.group(2))
                self.tasks.append("treinar"); continue
            m=re.match(r"([A-Za-zÀ-ÿ_]+)\s+(.+)$",line)
            if m and m.group(1).lower() in KEYS:
                key=KEYS[m.group(1).lower()]; value=m.group(2).strip().strip("\"'")
                if key in {"dados","saida","arquitetura"}: self.config[key]=value
                elif key=="taxa": self.config[key]=float(value)
                elif key=="quantizacao": self.config[key]=value.upper()
                else: self.config[key]=int(value)
                continue
            raise CompileError(f"linha {n}: instrução desconhecida: {line}")
        self.validate(); return self
    def validate(self):
        if self.config["arquitetura"].lower() not in {"llama","mistral","phi","qwen"}: raise CompileError("arquitetura não suportada pelo exportador: "+str(self.config["arquitetura"]))
        for k in ("dimensao","camadas","cabecas","contexto","vocabulario","passos"):
            if int(self.config[k])<=0: raise CompileError(k+" deve ser positivo")
        if self.config["dimensao"] % self.config["cabecas"]: raise CompileError("dimensao deve ser divisível por cabecas")
        if self.config["quantizacao"] not in {"F32","F16","Q8_0","Q4_K_M","Q4_0","Q5_K_M","Q6_K"}: raise CompileError("quantização não reconhecida")
    def manifest(self):
        return {"produto":"Intelink","linguagem":"Intelink Model Language","versao":VERSION,"nome":self.name,"modelo":self.config,"dados":self.data,"saida":self.output,"tarefas":self.tasks}
    def emit(self, directory):
        d=Path(directory); d.mkdir(parents=True,exist_ok=True)
        (d/"intelink_manifest.json").write_text(json.dumps(self.manifest(),ensure_ascii=False,indent=2),encoding="utf-8")
        cfg={"architectures":[self.config["arquitetura"].title()+"ForCausalLM"],"model_type":self.config["arquitetura"],"hidden_size":self.config["dimensao"],"num_hidden_layers":self.config["camadas"],"num_attention_heads":self.config["cabecas"],"max_position_embeddings":self.config["contexto"],"vocab_size":self.config["vocabulario"]}
        (d/"config.json").write_text(json.dumps(cfg,indent=2),encoding="utf-8")
        (d/"llama_cpp_commands.txt").write_text(self.commands(d),encoding="utf-8")
        return d
    def commands(self,d):
        out=["# Comandos gerados pela IntelinkC; revise caminhos antes de executar.","# 1) treine/obtenha pesos em formato Hugging Face compatível.","python convert_hf_to_gguf.py %s --outfile %s --outtype f16"%(shlex.quote(str(d)),shlex.quote(str(Path(self.output).with_suffix('.f16.gguf')))),"# 2) quantize para uso no llama.cpp:","llama-quantize %s %s %s"%(shlex.quote(str(Path(self.output).with_suffix('.f16.gguf'))),shlex.quote(self.output),shlex.quote(self.config['quantizacao']))]
        return "\n".join(out)+"\n"

def main():
    if len(sys.argv)<2 or sys.argv[1] in {"-h","--ajuda"}: print("Uso: intelinkc projeto.ilm [--emitir pasta] | --versao"); return
    if sys.argv[1] in {"--versao","-v"}: print(VERSION); return
    p=Path(sys.argv[1]); project=Project().parse(p.read_text(encoding="utf-8"))
    out=project.emit(sys.argv[sys.argv.index("--emitir")+1] if "--emitir" in sys.argv else p.with_suffix(".build"))
    print(json.dumps({"compilado":True,"nome":project.name,"diretorio":str(out),"manifesto":project.manifest()},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
