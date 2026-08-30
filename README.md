# Intelink Sandbox — computador na nuvem

## O que é

O **Intelink Sandbox** é a versão do ecossistema Intelink preparada para execução em um **computador Linux na nuvem ou ambiente sandbox**. Seu objetivo é permitir que os componentes Intelink sejam baixados, estudados, testados e executados fora do Android/Termux, com isolamento dos arquivos e dos processos locais.

A versão Termux/Android permanece separada no repositório [intelink-language](https://github.com/protagonistadasilva799-star/intelink-language). A diferença entre os repositórios é o ambiente de execução e a forma de preparação; os componentes, os créditos e os termos de uso continuam relacionados ao mesmo ecossistema Intelink.

**Criador:** Samuel Artulino.

## O que há nesta versão

A pasta `src/` reúne as implementações disponíveis. A pasta `bin/` contém lançadores que configuram automaticamente os caminhos necessários para os módulos se encontrarem no Linux. A pasta `data/` contém datasets e modelos locais incluídos no projeto. A pasta `terms/` preserva os termos de uso dos componentes de origem.

Os componentes presentes incluem Intelink AI, BotLang, Bridge, Chat, Language Runtime, Model Language, Model Zoo, Runtime Manager e Stable. Python é a tecnologia hospedeira utilizada em parte da implementação atual; isso não transforma automaticamente a linguagem, os formatos ou os comandos Intelink em Python.

## Como baixar

```bash
git clone --depth=1 https://github.com/protagonistadasilva799-star/intelink-sandbox.git
cd intelink-sandbox
```

## Como preparar

```bash
export PATH="$PWD/bin:$PATH"
export HOME="$PWD/home"
mkdir -p "$HOME"
```

A preparação usa diretórios locais dentro do sandbox e não exige a instalação de pacotes específicos do Termux.

## Primeiros testes

```bash
python3 -m compileall -q src
intelink doctor
intelink lista
intelink-zoo --help
intelink-botlang --ajuda
```

Outros lançadores disponíveis são `intelink-ai`, `intelink-bridge`, `intelink-chat`, `intelink-language`, `intelinkc` e `intelink-stable`.

## Programação e execução

Cada componente deve ser programado conforme a sintaxe e as interfaces implementadas no seu código. Para experimentar a IA local incluída:

```bash
intelink-ai --gerar "teste local no sandbox"
```

Para trabalhar com classificadores do Model Zoo:

```bash
intelink-zoo treinar --saida "$HOME/.intelink_zoo" --epocas 80
intelink-zoo prever "$HOME/.intelink_zoo/intelink_intent_pesos.py" "criar um programa"
```

Os exemplos acima exercitam componentes locais. Não presumem que exista um modelo externo ou um servidor de IA disponível.

## Dependências e limitações

O sandbox não é Termux. Comandos como `termux-toast`, `termux-battery-status` e outras integrações Android podem não existir. O diagnóstico também pode informar que Ollama, `llama.cpp` ou modelos GGUF não estão instalados. Recursos que dependem deles só funcionarão depois de uma configuração compatível e revisada.

Um pacote `.deb` criado para Termux/Android não deve ser instalado diretamente neste ambiente sem inspeção. Prefira os fontes e os lançadores deste repositório. Não coloque tokens, senhas, chaves ou dados pessoais em arquivos do projeto.

## Separação dos ambientes

| Ambiente | Repositório | Uso |
|---|---|---|
| Computador Linux na nuvem ou sandbox | `intelink-sandbox` | Testes isolados, execução local e adaptação dos componentes |
| Termux/Android | `intelink-language` e demais repositórios Termux | Execução no celular, integração com comandos e recursos Termux |

## Termos e autoria

Os termos de uso dos componentes estão preservados em `terms/`. Leia-os antes de usar, modificar, redistribuir ou publicar derivados. Publicações autorizadas devem preservar a atribuição exigida pelos projetos de origem.

**Criador:** Samuel Artulino.

## Intelink Check

O `intelink-check` é uma ferramenta de diagnóstico local. Ela verifica a presença dos arquivos essenciais, a versão do Python e a disponibilidade opcional de Ollama e `llama-cli`. A ferramenta não instala pacotes, não acessa a rede e não executa comandos externos.

```sh
export PATH="$PWD/bin:$PATH"
intelink-check
intelink-check --json
```

Dependências opcionais ausentes aparecem como `opcional`; isso não impede o diagnóstico do runtime básico. O relatório retorna código de saída zero quando os requisitos obrigatórios estão presentes.
