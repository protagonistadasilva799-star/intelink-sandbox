#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Intelink Runtime — gerenciador local de modelos para Termux.

Não é um fork do Ollama. É um runtime independente que organiza modelos GGUF,
seleciona o executor disponível e oferece um chat limpo sem logs técnicos.
"""
import argparse, json, os, shutil, subprocess, sys, time, urllib.error, urllib.request
from pathlib import Path

ROOT=Path.home()/".intelink"; REGISTRY=ROOT/"models.json"; SESSIONS=ROOT/"sessions"

def load_registry():
    try:return json.loads(REGISTRY.read_text(encoding="utf-8"))
    except Exception:return {"models":{},"default":None}
def save_registry(data):
    ROOT.mkdir(parents=True,exist_ok=True); REGISTRY.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
def safe_name(name):
    value="".join(c if c.isalnum() or c in "-_" else "-" for c in name.lower()).strip("-")
    return value[:60] or "modelo"

def add_model(path,name=None):
    p=Path(path).expanduser().resolve()
    if not p.is_file(): raise SystemExit("arquivo de modelo não encontrado: "+str(p))
    if p.suffix.lower()!=".gguf": raise SystemExit("o arquivo precisa terminar em .gguf")
    name=safe_name(name or p.stem); data=load_registry(); data["models"][name]={"name":name,"path":str(p),"bytes":p.stat().st_size,"added":time.time()}
    if not data.get("default"):data["default"]=name
    save_registry(data); return data["models"][name]
def list_models():
    data=load_registry(); rows=[]
    for name,item in data.get("models",{}).items():
        ok=Path(item["path"]).is_file(); rows.append({"nome":name,"padrao":name==data.get("default"),"existe":ok,"tamanho_mb":round(item.get("bytes",0)/1048576,2),"caminho":item["path"]})
    return rows
def choose(name=None):
    data=load_registry(); key=name or data.get("default")
    if not key or key not in data.get("models",{}):raise SystemExit("nenhum modelo registrado; use: intelink modelo adicionar ARQUIVO.gguf")
    item=data["models"][key]
    if not Path(item["path"]).is_file():raise SystemExit("modelo ausente: "+item["path"])
    return item

def ollama_chat(model,history,host):
    body=json.dumps({"model":model,"messages":history,"stream":True,"options":{"temperature":0.35,"repeat_penalty":1.15}}).encode()
    req=urllib.request.Request(host.rstrip("/")+"/api/chat",data=body,headers={"Content-Type":"application/json"})
    answer=[]
    with urllib.request.urlopen(req,timeout=900) as response:
        for raw in response:
            if not raw.strip():continue
            try:
                msg=json.loads(raw.decode("utf-8","replace")); piece=msg.get("message",{}).get("content","")
                if piece:print(piece,end="",flush=True);answer.append(piece)
            except (ValueError,UnicodeDecodeError):continue
    print();return "".join(answer)

def llama_chat(path,prompt,binary="llama-cli",context=2048):
    cmd=[binary,"-m",path,"-p",prompt,"-n","512","-c",str(context),"--simple-io","--no-display-prompt"]
    try:
        run=subprocess.run(cmd,capture_output=True,text=True,timeout=900)
    except FileNotFoundError:raise SystemExit("llama-cli não encontrado no PATH")
    if run.returncode!=0:raise SystemExit("llama.cpp falhou; detalhes técnicos foram ocultados. Código: "+str(run.returncode))
    text=run.stdout.strip();print(text);return text

def clean_chat(model,backend,host,binary):
    history=[]; print("Intelink Chat\nDigite /sair para encerrar, /limpar para apagar a sessão.\n")
    while True:
        try:prompt=input("Você: ").strip()
        except (EOFError,KeyboardInterrupt):print();break
        if not prompt:continue
        if prompt=="/sair":break
        if prompt=="/limpar":history=[];print("Sessão limpa.\n");continue
        history.append({"role":"user","content":prompt})
        try:
            print("Intelink: ",end="")
            if backend=="ollama":answer=ollama_chat(model,history,host)
            elif backend=="llama.cpp":answer=llama_chat(model["path"],prompt,binary)
            else:
                try:answer=ollama_chat(model,history,host)
                except Exception:answer=llama_chat(model["path"],prompt,binary)
            if backend!="llama.cpp":history.append({"role":"assistant","content":answer})
            print()
        except (urllib.error.URLError,TimeoutError,RuntimeError) as exc:history.pop();print("Não foi possível iniciar o executor local.")

def doctor():
    return {"python":sys.version.split()[0],"termux":bool(os.environ.get("PREFIX")),"ollama":shutil.which("ollama") is not None,"llama_cli":shutil.which("llama-cli") is not None,"modelos":len(load_registry().get("models",{})),"diretorio":str(ROOT)}

def main():
    ap=argparse.ArgumentParser(prog="intelink",description="Runtime Intelink para modelos locais")
    sub=ap.add_subparsers(dest="cmd")
    sub.add_parser("lista",help="listar modelos registrados")
    sub.add_parser("doctor",help="verificar ambiente")
    add=sub.add_parser("adicionar",help="registrar um modelo GGUF");add.add_argument("arquivo");add.add_argument("--nome")
    chat=sub.add_parser("chat",help="abrir chat limpo");chat.add_argument("--modelo");chat.add_argument("--backend",choices=["auto","ollama","llama.cpp"],default="auto");chat.add_argument("--host",default=os.environ.get("OLLAMA_HOST","http://127.0.0.1:11434"));chat.add_argument("--binario",default="llama-cli")
    args=ap.parse_args()
    if args.cmd=="lista":print(json.dumps(list_models(),ensure_ascii=False,indent=2));return
    if args.cmd=="doctor":print(json.dumps(doctor(),ensure_ascii=False,indent=2));return
    if args.cmd=="adicionar":print(json.dumps(add_model(args.arquivo,args.nome),ensure_ascii=False,indent=2));return
    if args.cmd=="chat":
        if args.backend=="ollama":
            item=args.modelo or "llama3.2"
        else:
            item=choose(args.modelo)
        clean_chat(item,args.backend,args.host,args.binario);return
    ap.print_help()
if __name__=="__main__":main()
