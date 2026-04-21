# Inspector Performance Runbook

## Como ativar

Use qualquer uma das opções:

```js
localStorage.tarielPerf = "1"
```

ou abra a aplicação com:

```text
/app/?perf=1
```

Para desligar:

```js
localStorage.removeItem("tarielPerf")
```

Depois faça um hard reload.

## Fluxo recomendado de medição

1. Abra o console.
2. Rode `window.TarielPerf.clear()`.
3. Recarregue a página ainda com `perf` ativo.
4. Espere o portal ficar utilizável.
5. Execute a sequência abaixo:
   - abrir `Novo Chat`
   - digitar e enviar a primeira mensagem
   - esperar a focused conversation
   - abrir um laudo pelos recentes
   - alternar entre `chat` e `anexos`
   - abrir `Nova Inspeção`
   - carregar pendências
   - abrir o widget da mesa, se aplicável

## Coleta do relatório

Resumo rápido:

```js
window.TarielPerf.printSummary()
```

Maiores custos:

```js
window.TarielPerf.topFunctions()
window.TarielPerf.topNetwork()
window.TarielPerf.topLongTasks()
```

Relatório completo:

```js
window.TarielPerf.getReport()
```

Para copiar o JSON completo:

```js
copy(JSON.stringify(window.TarielPerf.getReport(), null, 2))
```

## Como interpretar

### Boot

- `navigation.domContentLoadedMs` e `navigation.loadMs` mostram o custo bruto de navegação.
- `boot` e `marks` mostram quando portal, workspace e composer ficaram utilizáveis.

### Rede vs frontend

- `network` mostra o tempo total das requisições.
- `functions`, `state` e `render` mostram o que o frontend fez depois que a resposta chegou.
- Se a rede for rápida e `render`/`state` dominarem, o gargalo está no cliente.

### Sincronização excessiva

Olhe:

- `functions` com nome `inspetor.sincronizarEstadoInspector`
- `state` com `resolveInspectorScreen`, `aplicarMatrizVisibilidadeInspector`, `sincronizarInspectorScreen`
- `counters` para `inspetor.dataset.sync` e `inspetor.storage.sync`

Se esses números crescerem demais por um clique, há cascata de sincronização.

### Observers e listeners

Olhe:

- `listeners.total`
- `listeners.duplicates`
- `observers.callbacks`
- `observers.byLabel`

Se `workspace` ou `sidebarHistorico` dispararem muito para uma ação pequena, o custo está sendo empurrado por mutação de DOM.

### DOM

Use `domSnapshots` para comparar:

- boot
- entrada em `assistant_landing`
- focused conversation
- histórico renderizado
- pendências carregadas

Se a contagem de nós ou `scrollHeight` cresce muito, a tela provavelmente está pagando por render/layout.

## Sequências úteis de diagnóstico

### Carga inicial lenta

```js
window.TarielPerf.clear()
location.reload()
```

Depois leia:

```js
window.TarielPerf.printSummary()
```

### Clique em Novo Chat

```js
window.TarielPerf.clear()
```

Clique em `Novo Chat` e depois rode:

```js
window.TarielPerf.getReport().transitions
```

### Primeira mensagem do Novo Chat

Envie a primeira mensagem e depois rode:

```js
window.TarielPerf.getReport().transitions
window.TarielPerf.topFunctions()
```

### Abertura de laudo

Abra um laudo recente e depois rode:

```js
window.TarielPerf.topFunctions()
window.TarielPerf.getReport().domSnapshots.slice(-5)
```

## Observações

- A instrumentação fica toda protegida por modo `perf`.
- Fora desse modo, o comportamento da aplicação permanece igual.
- Esta fase é só de medição e documentação. Não interpreta os dados automaticamente nem aplica correções.
