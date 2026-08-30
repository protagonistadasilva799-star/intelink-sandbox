#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Intelink Clean Chat para Termux.
Mostra somente texto do assistente. Logs do processo ficam ocultos.

Uso:
  python3 intelink_chat.py --model llama3.2
  python3 intelink_chat.py --backend llama.cpp --model ./modelo.gguf
"""
import argparse, json, os, subprocess, sys, urllib.error, urllib.request

class CleanChat:
    def __init__(self, backend="auto", model="llama3.2", host="http://127.0.0.1:11434", binary="llama-cli"):
        self.backend, self.model, self.host, self.binary = backend, model, host.rstrip("/"), binary
        self.history=[]
    def ollama_available(self):
        try:
            with urllib.request.urlopen(self.host+"/api/tags",timeout=2): return True
        except Exception: return False
    def ask_ollama(self, prompt):
        self.history += [{"role":"user","content":prompt}]
        body=json.dumps({"model":self.model,"messages":self.history,"stream":True}).encode()
        req=urllib.request.Request(self.host+"/api/chat",data=body,headers={"Content-Type":"application/json"})
        answer=[]
        try:
            with urllib.request.urlopen(req,timeout=600) as response:
                for raw in response:
                    if not raw.strip(): continue
                    try:
                        item=json.loads(raw.decode("utf-8","replace")); piece=item.get("message",{}).get("content","")
                        if piece: print(piece,end="",flush=True); answer.append(piece)
                    except (ValueError,UnicodeDecodeError): continue
            print(); text="".join(answer); self.history += [{"role":"assistant","content":text}]; return text
        except (urllib.error.URLError,TimeoutError) as exc:
            self.history.pop(); raise RuntimeError("Ollama não está acessível: "+str(exc))
    def ask_llama(self, prompt):
        cmd=[self.binary,"-m",self.model,"-p",prompt,"-n","512","--simple-io","--no-display-prompt"]
        try:
            p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,timeout=600)
            text=p.stdout.strip()
            if text: print(text)
            if p.returncode: raise RuntimeError("llama.cpp encerrou com código "+str(p.returncode))
            return text
        except FileNotFoundError: raise RuntimeError("llama.cpp não encontrado: "+self.binary)
    def ask(self,prompt):
        if self.backend=="ollama" or (self.backend=="auto" and self.ollama_available()): return self.ask_ollama(prompt)
        return self.ask_llama(prompt)
    def run(self):
        print("Intelink Chat")
        print("Digite /sair para encerrar ou /limpar para apagar o histórico.\n")
        while True:
            try: prompt=input("Você: ").strip()
            except (EOFError,KeyboardInterrupt): print(); break
            if not prompt: continue
            if prompt=="/sair": break
            if prompt=="/limpar": self.history=[]; print("Histórico limpo.\n"); continue
            try: print("Intelink: ",end=""); self.ask(prompt); print()
            except RuntimeError as exc: print("Não foi possível iniciar a IA: "+str(exc))

def main():
    ap=argparse.ArgumentParser(description="Chat limpo Intelink para Ollama/llama.cpp")
    ap.add_argument("--backend",choices=["auto","ollama","llama.cpp"],default="auto")
    ap.add_argument("--model",default="llama3.2",help="nome do modelo Ollama ou caminho GGUF")
    ap.add_argument("--host",default=os.environ.get("OLLAMA_HOST","http://127.0.0.1:11434"))
    ap.add_argument("--binary",default="llama-cli")
    ap.add_argument("--prompt",help="faz uma pergunta única sem abrir o modo interativo")
    args=ap.parse_args(); chat=CleanChat(args.backend,args.model,args.host,args.binary)
    if args.prompt: chat.ask(args.prompt)
    else: chat.run()
if __name__=="__main__": main()
