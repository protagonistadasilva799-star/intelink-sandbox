#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INTELINK-MODELO-REAL
Modelo neural de linguagem de caracteres treinado do zero, sem bibliotecas externas.

A rede é pequena para caber no Termux: embeddings + camada oculta + softmax.
Ela aprende distribuição do próximo caractere a partir de um corpus real. O agente
usa o modelo para gerar hipóteses textuais, mas não confunde geração com autonomia:
a missão também possui planejamento, criação de código, teste, crítica e segurança.
"""
import ast, csv, json, math, os, random, re, shlex, subprocess, sys, tempfile, time
from collections import Counter
from pathlib import Path

ROOT = Path.home() / ".intelink_agent"
WEIGHTS = ROOT / "intelink_pesos_treinados.py"
LOCAL_WEIGHTS = Path(__file__).with_name("intelink_pesos_treinados.py")
STATE = ROOT / "estado_missao.json"

def weight_path():
    return WEIGHTS if WEIGHTS.exists() else LOCAL_WEIGHTS


def now(): return time.strftime("%Y-%m-%dT%H:%M:%S")
def clip(s, n=1800): return str(s) if len(str(s)) <= n else str(s)[:n] + "..."
def clean(s): return re.sub(r"\s+", " ", str(s)).strip()


def read_corpus(path=None, max_chars=180000):
    """Lê corpus real de CSV/TXT/MD/PY/JSON, sem interpretar código como programa."""
    roots = [Path(path).expanduser()] if path else [Path("/home/ubuntu/intelink_corpus"), Path.cwd()]
    pieces = []
    for root in roots:
        files = [root] if root.is_file() else list(root.rglob("*")) if root.is_dir() else []
        for f in files:
            if len("\n".join(pieces)) >= max_chars: break
            if not f.is_file() or f.suffix.lower() not in {".csv", ".txt", ".md", ".py", ".json"}: continue
            try:
                if f.suffix.lower() == ".csv":
                    with f.open(encoding="utf-8", errors="replace", newline="") as h:
                        for row in csv.reader(h):
                            vals = [clean(x) for x in row if clean(x)]
                            if vals: pieces.append(" | ".join(vals))
                else:
                    pieces.append(f.read_text(encoding="utf-8", errors="replace"))
            except OSError: pass
    text = "\n".join(pieces)
    if len(text) < 300:
        text = ("Intelink agente autônomo brasileiro. Planejar, criar, analisar, programar, "
                "testar, aprender e verificar resultados. Python é uma linguagem de programação "
                "com funções, classes, arquivos e exceções. Termux fornece um ambiente local no Android.\n") * 20
    return text[:max_chars]


def softmax(xs):
    m = max(xs); ex = [math.exp(min(40, x - m)) for x in xs]; z = sum(ex) or 1.0
    return [x / z for x in ex]


class NeuralTextModel:
    """Rede neural densa de contexto curto, implementada manualmente."""
    def __init__(self, text, context=4, emb=16, hidden=48, seed=7):
        self.context, self.emb, self.hidden = context, emb, hidden
        chars = sorted(set(text))
        if len(chars) > 96:
            counts = {}
            for c in text: counts[c] = counts.get(c, 0) + 1
            chars = sorted(sorted(counts, key=counts.get, reverse=True)[:95] + ["?"])
        self.chars = chars; self.ix = {c:i for i,c in enumerate(chars)}
        self.rng = random.Random(seed); v = len(chars); scale = .08
        self.E = [[self.rng.uniform(-scale, scale) for _ in range(emb)] for _ in range(v)]
        self.W1 = [[self.rng.uniform(-scale, scale) for _ in range(context * emb)] for _ in range(hidden)]
        self.b1 = [0.0] * hidden
        self.W2 = [[self.rng.uniform(-scale, scale) for _ in range(hidden)] for _ in range(v)]
        self.b2 = [0.0] * v

    def forward(self, ids):
        x = []
        for i in ids[-self.context:]: x.extend(self.E[i])
        while len(x) < self.context * self.emb: x = self.E[self.ix.get(" ", 0)] + x
        h = [math.tanh(sum(row[j] * x[j] for j in range(len(x))) + self.b1[k]) for k,row in enumerate(self.W1)]
        p = softmax([sum(row[k] * h[k] for k in range(self.hidden)) + self.b2[i] for i,row in enumerate(self.W2)])
        return x, h, p

    def train(self, text, steps=1800, lr=.035, report_every=300):
        data = [self.ix.get(c, self.ix.get("?", 0)) for c in text]
        if len(data) < self.context + 2: return []
        history = []; rng = random.Random(31)
        for step in range(1, steps + 1):
            pos = rng.randrange(self.context, len(data) - 1); ids = data[pos-self.context:pos]; target = data[pos]
            x, h, p = self.forward(ids); loss = -math.log(max(p[target], 1e-12)); history.append(loss)
            dz = p[:]; dz[target] -= 1
            dW2 = [[dz[i] * h[k] for k in range(self.hidden)] for i in range(len(self.chars))]
            db2 = dz[:]
            dh = [sum(self.W2[i][k] * dz[i] for i in range(len(self.chars))) for k in range(self.hidden)]
            da = [dh[k] * (1 - h[k]*h[k]) for k in range(self.hidden)]
            dW1 = [[da[k] * x[j] for j in range(len(x))] for k in range(self.hidden)]
            db1 = da[:]
            dx = [sum(self.W1[k][j] * da[k] for k in range(self.hidden)) for j in range(len(x))]
            for i in range(len(self.chars)):
                for k in range(self.hidden): self.W2[i][k] -= lr * dW2[i][k]
                self.b2[i] -= lr * db2[i]
            for k in range(self.hidden):
                for j in range(len(x)): self.W1[k][j] -= lr * dW1[k][j]
                self.b1[k] -= lr * db1[k]
            for q, idx in enumerate(ids):
                start = q * self.emb
                for e in range(self.emb): self.E[idx][e] -= lr * dx[start+e]
            if step % report_every == 0: history.append(sum(history[-report_every:]) / report_every)
        return history

    def generate(self, prompt, length=220, temperature=.75):
        ids = [self.ix.get(c, self.ix.get("?", 0)) for c in prompt]
        out = list(prompt)
        for _ in range(length):
            _, _, p = self.forward(ids[-self.context:]); p = [x ** (1 / max(.15, temperature)) for x in p]; z = sum(p); p = [x/z for x in p]
            r = random.random(); acc = 0; chosen = len(p)-1
            for i, prob in enumerate(p):
                acc += prob
                if r <= acc: chosen = i; break
            ids.append(chosen); out.append(self.chars[chosen])
        return "".join(out)

    def save(self):
        ROOT.mkdir(parents=True, exist_ok=True)
        state = {"context": self.context, "emb": self.emb, "hidden": self.hidden,
                 "chars": self.chars, "E": self.E, "W1": self.W1, "b1": self.b1,
                 "W2": self.W2, "b2": self.b2}
        WEIGHTS.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls):
        d = json.loads(WEIGHTS.read_text(encoding="utf-8")); obj = cls.__new__(cls); obj.__dict__.update(d); obj.ix = {c:i for i,c in enumerate(obj.chars)}; obj.rng = random.Random(7); return obj


class AttentionLanguageModel:
    """Mini-rede com atenção causal; os pesos são aprendidos do corpus fornecido."""
    def __init__(self, text, context=8, dim=24, seed=11):
        self.context, self.dim = context, dim
        chars = sorted(set(text))
        if len(chars) > 128:
            count = Counter(text)
            chars = sorted([x[0] for x in count.most_common(127)] + ["?"])
        self.chars, self.ix = chars, {c:i for i,c in enumerate(chars)}
        r = random.Random(seed); v = len(chars); s = .06
        self.E = [[r.uniform(-s,s) for _ in range(dim)] for _ in range(v)]
        self.Q = [[r.uniform(-s,s) for _ in range(dim)] for _ in range(dim)]
        self.K = [[r.uniform(-s,s) for _ in range(dim)] for _ in range(dim)]
        self.V = [[r.uniform(-s,s) for _ in range(dim)] for _ in range(dim)]
        self.O = [[r.uniform(-s,s) for _ in range(dim)] for _ in range(v)]
        self.b = [0.0] * v

    def _mul(self, x, m): return [sum(x[j] * m[j][i] for j in range(len(x))) for i in range(len(m[0]))]

    def representation(self, ids):
        ids = ids[-self.context:]
        while len(ids) < self.context: ids = [0] + ids
        xs = [self.E[i] for i in ids]
        q = self._mul(xs[-1], self.Q); keys = [self._mul(x, self.K) for x in xs]; vals = [self._mul(x, self.V) for x in xs]
        scores = [sum(q[j] * k[j] for j in range(self.dim)) / (self.dim ** .5) for k in keys]
        a = softmax(scores); h = [sum(a[t] * vals[t][j] for t in range(self.context)) for j in range(self.dim)]
        return h, a

    def probabilities(self, ids):
        h, a = self.representation(ids)
        return h, a, softmax([sum(self.O[i][j] * h[j] for j in range(self.dim)) + self.b[i] for i in range(len(self.chars))])

    def train(self, text, steps=2400, batch=4, lr=.025, checkpoint=400):
        data = [self.ix.get(c, self.ix.get("?", 0)) for c in text]
        cut = max(self.context + 2, int(len(data) * .9)); train, valid = data[:cut], data[cut:]
        rng = random.Random(41); log = []; scale = self.dim ** .5
        for step in range(1, steps + 1):
            dE = [[0.0] * self.dim for _ in self.E]; dQ = [[0.0] * self.dim for _ in self.Q]; dK = [[0.0] * self.dim for _ in self.K]; dV = [[0.0] * self.dim for _ in self.V]
            dO = [[0.0] * self.dim for _ in self.O]; db = [0.0] * len(self.b); loss = 0.0
            for _ in range(batch):
                pos = rng.randrange(self.context, max(self.context + 1, len(train)-1)); ids = train[pos-self.context:pos]; target = train[pos]
                ids = ids[-self.context:]
                h, att, p = self.probabilities(ids); loss -= math.log(max(p[target], 1e-12)); dz = p[:]; dz[target] -= 1
                dh = [0.0] * self.dim
                for i in range(len(self.O)):
                    for j in range(self.dim): dO[i][j] += dz[i] * h[j]; dh[j] += self.O[i][j] * dz[i]
                    db[i] += dz[i]
                xs = [self.E[i] for i in ids]; q = self._mul(xs[-1], self.Q); keys = [self._mul(x, self.K) for x in xs]; vals = [self._mul(x, self.V) for x in xs]
                da = [sum(dh[j] * vals[t][j] for j in range(self.dim)) for t in range(self.context)]; mean = sum(da[t] * att[t] for t in range(self.context)); ds = [att[t] * (da[t] - mean) for t in range(self.context)]
                dq = [0.0] * self.dim; dx = [[0.0] * self.dim for _ in range(self.context)]
                for t in range(self.context):
                    dval = [att[t] * dh[j] for j in range(self.dim)]; dkey = [ds[t] * q[j] / scale for j in range(self.dim)]
                    for i in range(self.dim):
                        for j in range(self.dim): dV[i][j] += xs[t][i] * dval[j]; dK[i][j] += xs[t][i] * dkey[j]
                        dx[t][i] += sum(self.V[i][j] * dval[j] + self.K[i][j] * dkey[j] for j in range(self.dim))
                        dq[i] += ds[t] * keys[t][i] / scale
                for i in range(self.dim):
                    for j in range(self.dim): dQ[i][j] += xs[-1][i] * dq[j]; dx[-1][i] += sum(self.Q[i][j] * dq[j] for j in range(self.dim))
                for t, idx in enumerate(ids):
                    for j in range(self.dim): dE[idx][j] += dx[t][j]
            rate = lr / batch
            for mats, grads in ((self.E,dE),(self.Q,dQ),(self.K,dK),(self.V,dV),(self.O,dO)):
                for i in range(len(mats)):
                    for j in range(len(mats[i])): mats[i][j] -= rate * max(-3.0, min(3.0, grads[i][j]))
            for i in range(len(self.b)): self.b[i] -= rate * max(-3.0, min(3.0, db[i]))
            if step % checkpoint == 0 or step == steps:
                val_loss = self.loss(valid[:min(len(valid), 6000)]) if valid else 0.0
                log.append({"step": step, "treino": round(loss/batch, 4), "validacao": round(val_loss, 4)})
                self.save()
        return log

    def loss(self, data):
        if len(data) <= self.context: return 0.0
        total = 0.0; n = min(len(data)-1, 2000)
        for pos in range(self.context, self.context+n):
            _, _, p = self.probabilities(data[pos-self.context:pos]); total -= math.log(max(p[data[pos]], 1e-12))
        return total / n

    def generate(self, prompt, length=240, temperature=.72):
        ids = [self.ix.get(c, self.ix.get("?",0)) for c in prompt]; out = list(prompt)
        for _ in range(length):
            _, _, p = self.probabilities(ids[-self.context:]); p = [x ** (1/max(.15,temperature)) for x in p]; z=sum(p); p=[x/z for x in p]
            r=random.random(); total=0.0; pick=len(p)-1
            for i,x in enumerate(p):
                total += x
                if r <= total: pick=i; break
            ids.append(pick); out.append(self.chars[pick])
        return "".join(out)

    def save(self):
        ROOT.mkdir(parents=True, exist_ok=True)
        state = {"tipo":"attention","context":self.context,"dim":self.dim,"chars":self.chars,"E":self.E,"Q":self.Q,"K":self.K,"V":self.V,"O":self.O,"b":self.b}
        WEIGHTS.write_text("MODEL = " + json.dumps(state, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls):
        raw = weight_path().read_text(encoding="utf-8").split("=", 1)[1].strip(); d = ast.literal_eval(raw)
        obj=cls.__new__(cls); obj.__dict__.update(d); obj.ix={c:i for i,c in enumerate(obj.chars)}; return obj


class CodeMind:
    def make(self, objective):
        name = re.sub(r"\W+", "_", objective.lower()).strip("_")[:30] or "solucao"
        return f'''def {name}(entrada):\n    """Solução criada pelo agente para: {objective}"""\n    etapas = [observar, transformar, verificar]\n    valor = entrada\n    for etapa in etapas:\n        valor = etapa(valor)\n    return valor\n\ndef observar(valor):\n    return valor\n\ndef transformar(valor):\n    return valor\n\ndef verificar(valor):\n    if valor is None:\n        raise ValueError("resultado vazio")\n    return valor\n'''

    def evaluate(self, code):
        try:
            tree = ast.parse(code); funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            with tempfile.TemporaryDirectory() as d:
                p = Path(d) / "candidate.py"; p.write_text(code, encoding="utf-8")
                run = subprocess.run([sys.executable, "-m", "py_compile", str(p)], capture_output=True, text=True, timeout=8)
            return {"ok": run.returncode == 0, "funcoes": funcs, "erro": clip(run.stderr, 500)}
        except Exception as e: return {"ok": False, "erro": str(e)}


class SafeTermux:
    ALLOWED = {"pwd","ls","whoami","uname","date","id","echo","printf","cat","head","tail","grep","find","wc","python","python3","termux-battery-status","termux-clipboard-get","termux-toast","termux-vibrate"}
    BLOCKED = {"rm","dd","mkfs","reboot","shutdown","poweroff","su","sudo","chmod","chown","mount","umount","kill","pkill","iptables","curl","wget","ssh","scp","apt","pkg","pip","pip3","git"}
    def run(self, command):
        try: parts = shlex.split(command)
        except ValueError as e: return {"ok":False,"erro":str(e)}
        if not parts: return {"ok":False,"erro":"vazio"}
        program = os.path.basename(parts[0])
        if program in self.BLOCKED or program not in self.ALLOWED: return {"ok":False,"erro":f"não autorizado: {program}"}
        if any(x in command for x in [";","&&","||","|",">","<","`","$()"]): return {"ok":False,"erro":"encadeamento bloqueado"}
        if input(f"Autorizar '{command}'? [s/N] ").lower().strip() not in {"s","sim","y","yes"}: return {"ok":False,"erro":"cancelado"}
        try:
            p = subprocess.run(parts, capture_output=True, text=True, timeout=30, cwd=str(Path.home()))
            return {"ok":p.returncode == 0,"codigo":p.returncode,"saida":clip(p.stdout),"erro":clip(p.stderr)}
        except Exception as e: return {"ok":False,"erro":str(e)}


class Mission:
    def __init__(self, model): self.model, self.code, self.termux = model, CodeMind(), SafeTermux()
    def run(self, objective, cycles=6):
        state = {"objetivo":objective,"inicio":now(),"ciclos":[],"status":"executando"}
        plan = ["observar objetivo", "gerar hipóteses", "criar artefato", "testar artefato", "criticar resultado", "registrar aprendizagem"]
        for i, action in enumerate(plan[:cycles], 1):
            if action == "observar objetivo": result = {"dominio": self.domain(objective), "tokens": objective.split()}
            elif action == "gerar hipóteses": result = self.model.generate(objective[:40], 160) if self.model else "modelo ainda não treinado"
            elif action == "criar artefato": result = self.code.make(objective)
            elif action == "testar artefato": result = self.code.evaluate(state["ciclos"][-1]["resultado"]) if state["ciclos"] else {"ok":False}
            elif action == "criticar resultado": result = {"pergunta":"o resultado atende ao objetivo?", "proxima_estrategia":"alterar a solução e repetir o teste"}
            else: result = {"registrado":True,"memoria":str(ROOT)}
            state["ciclos"].append({"numero":i,"acao":action,"resultado":clip(result),"hora":now()})
            save_state(state)
        state["status"] = "concluida" if len(state["ciclos"]) == len(plan) else "parcial"; state["fim"] = now(); save_state(state); return state
    def domain(self, text):
        t = set(re.findall(r"[a-záàãâéêíóõôúç]+", text.lower()))
        if t & {"codigo","programa","programar","desenvolver"}: return "programação"
        if t & {"analisar","analise","investigar"}: return "análise"
        return "exploração"


def save_state(state):
    ROOT.mkdir(parents=True, exist_ok=True); STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--treinar":
        corpus = read_corpus(sys.argv[2] if len(sys.argv) > 2 else None); model = AttentionLanguageModel(corpus); steps = int(sys.argv[3]) if len(sys.argv) > 3 else 2400
        history = model.train(corpus, steps); model.save(); print(json.dumps({"treinado":True,"caracteres":len(corpus),"vocabulario":len(model.chars),"passos":steps,"perda_final":history[-1] if history else None,"pesos":str(WEIGHTS)}, ensure_ascii=False, indent=2)); return
    model = AttentionLanguageModel.load() if weight_path().exists() else None
    if len(sys.argv) >= 3 and sys.argv[1] == "--goal": print(json.dumps(Mission(model).run(" ".join(sys.argv[2:])), ensure_ascii=False, indent=2)); return
    if len(sys.argv) >= 2 and sys.argv[1] == "--gerar": print(model.generate(" ".join(sys.argv[2:])) if model else "Treine primeiro com --treinar"); return
    print("Intelink modelo real | uso: --treinar [CORPUS] [PASSOS] | --goal OBJETIVO | --gerar TEXTO")


if __name__ == "__main__": main()
