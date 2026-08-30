# Intelink Sandbox

## O que é este projeto

O **Intelink Sandbox** é uma adaptação do ecossistema Intelink para computador Linux na nuvem e ambientes sandbox. Ele reúne implementações de linguagem, runtime, IA, modelos, chat e ferramentas auxiliares, mantendo os repositórios destinados ao Termux/Android separados.

**Criador:** Samuel Artulino.

Esta pasta é uma cópia isolada dos componentes implementados, muitos deles usando Python como tecnologia hospedeira. Python é a tecnologia de implementação; os formatos, comandos e linguagens Intelink devem ser conferidos nos respectivos executores e parsers. Os repositórios Termux originais permanecem separados e não são substituídos por esta adaptação.

## O que foi encontrado

Não foi encontrado um `manifest.json`, `package.json` de extensão de navegador, `.crx` ou `.zip` de WebExtension. O material disponível é uma suíte de ferramentas Python originalmente direcionada ao Termux/Android, com estes componentes: Intelink AI, BotLang, Bridge, Chat, Language Runtime, Model Language, Model Zoo, Runtime Manager e Stable.

A adaptação mantém os fontes em `src/`, reúne o dataset e os modelos locais em `data/` e cria lançadores em `bin/` que configuram `PYTHONPATH` automaticamente para que os módulos relacionados consigam importar uns aos outros no Linux do sandbox.

## Execução

A partir desta pasta:

```bash
export PATH="$PWD/bin:$PATH"
export HOME="$PWD/home"
mkdir -p "$HOME"

intelink doctor
intelink lista
intelink-zoo --help
intelink-ai --gerar "teste local no sandbox"
intelink-botlang --ajuda
```

Os demais lançadores são `intelink-bridge`, `intelink-chat`, `intelink-language`, `intelinkc` e `intelink-stable`.

## Dependências e limites

Os componentes testados usam Python e biblioteca padrão. A verificação de sintaxe foi concluída sem erros. O comando `intelink doctor` confirma que o ambiente sandbox não é Termux e que não há Ollama, `llama.cpp` ou modelos GGUF registrados. Portanto, os fluxos de geração local e classificação funcionam, enquanto os fluxos que exigem um modelo GGUF, Ollama ou executores nativos precisam de configuração adicional.

O comando `intelink-ai --gerar` foi executado com sucesso no sandbox. O conteúdo gerado é um resultado do modelo local incluído no projeto e não uma resposta de um LLM externo.

## Teste de sintaxe

```bash
python3 -m compileall -q src
```

## Documentação técnica

Os READMEs dos componentes e os termos de uso foram preservados na pasta `terms/`. Consulte a documentação de cada componente antes de programar, redistribuir ou publicar derivados.

## Origem

A cópia foi montada a partir dos repositórios públicos acessíveis na conta GitHub conectada, incluindo `intelink-ai`, `intelink-botlang`, `intelink-bridge`, `intelink-chat`, `intelink-language`, `intelink-model-language`, `intelink-model-zoo`, `intelink-runtime`, `intelink-stable` e `intelink-launch-kit`.

Consulte os respectivos `README.md` e `TERMS.md` nos repositórios originais antes de redistribuir ou publicar o material. Os avisos de crédito e as condições de uso originais foram preservados conceitualmente; esta adaptação não concede direitos adicionais.
