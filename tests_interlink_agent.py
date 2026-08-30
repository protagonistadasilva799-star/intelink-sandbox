#!/usr/bin/env python3
import json
import os
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent
env = os.environ.copy()
env.update({'HOME': '/home/ubuntu', 'PYTHONPATH': str(root / 'src'), 'PATH': f'{root / "bin"}:{env.get("PATH", "")}'})
cases = [
    ('pergunta_fontes', ['bin/intelink-agent', '--perguntar', 'como funciona a memória do runtime', '--sem-geracao', '--json']),
    ('autoria', ['bin/intelink-agent', '--perguntar', 'quem desenvolveu o Interlink AI', '--sem-geracao', '--json']),
    ('codigo', ['bin/intelink-agent', '--criar', 'criar uma função para validar memória', '--json']),
]
report = []
for name, command in cases:
    p = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=30)
    item = {'caso': name, 'codigo_retorno': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}
    if p.returncode == 0:
        parsed = json.loads(p.stdout)
        if name == 'codigo':
            item['sintaxe'] = parsed.get('validacao_sintatica')
            item['nao_executado'] = parsed.get('executado') is False
        else:
            item['fontes'] = len(parsed.get('fontes', []))
            item['tem_plano'] = bool(parsed.get('plano', {}).get('passos'))
            item['identidade'] = parsed.get('identidade')
    report.append(item)
(root / 'AGENT_ACCEPTANCE_REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
