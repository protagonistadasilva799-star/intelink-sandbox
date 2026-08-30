# Interlink AI no Ollama

Esta pasta contém um `Modelfile.interlink-ai` para executar o checkpoint GGUF local com a identidade **Interlink AI — desenvolvido por Samuel**.

## Importação

Coloque o arquivo GGUF no mesmo caminho relativo indicado no Modelfile, ou ajuste a linha `FROM`. Depois execute:

```sh
ollama create interlink-ai -f Modelfile.interlink-ai
ollama run interlink-ai
```

Para uma pergunta direta:

```sh
ollama run interlink-ai "Explique o que é o Interlink AI."
```

## Limitações

O Modelfile altera o prompt de sistema, o template de conversa e os parâmetros de geração. Ele **não altera os pesos** do GGUF. A saída pode continuar curta, repetitiva ou pouco coerente porque o checkpoint original não possui um template explícito de chat e ainda não foi retreinado diretamente.

O perfil usa `num_ctx 512`, `num_predict 192` e penalidade de repetição para reduzir consumo e loops em celulares modestos. O desempenho real no Galaxy A10s depende da versão do Ollama/llama.cpp, memória livre, armazenamento e suporte do sistema.

Para retreinamento real, é necessário um checkpoint-fonte treinável ou uma reconstrução em PyTorch/Safetensors. O GGUF original permanece preservado e não deve ser sobrescrito.
