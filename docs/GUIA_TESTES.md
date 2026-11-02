# Guia de Testes — Manuais e Automatizados

## Parte 1 — Testes automatizados (ja executados)

Comando executado durante o desenvolvimento:

```bash
pytest
```

**Resultado real obtido:** `19 passed, 1 warning in 0.57s`
(warning e apenas uma `DeprecationWarning` interna do Starlette,
sem relacao com a logica da aplicacao).

A suite (`tests/test_api.py`, 19 testes) usa um banco SQLite isolado,
criado em um diretorio temporario por sessao de teste (ver
`tests/conftest.py`), e cobre:

1. Health check.
2. Cadastro valido (201).
3. Validacao de cadastro invalido (titulo ausente, vazio, excedendo o
   tamanho maximo — 422).
4. Listagem sem tarefas.
5. Listagem com tarefas (ordem deterministica por id).
6. Paginacao (`skip`/`limit`) e validacao de parametros invalidos.
7. Consulta de ID existente.
8. Consulta de ID inexistente (404).
9. Atualizacao valida (200) e invalida (422).
10. Atualizacao de ID inexistente (404).
11. Exclusao valida (204) e de ID inexistente (404).
12. Persistencia apos reabrir uma nova conexao com o SQLite.
13. Consistencia dos schemas JSON de resposta (criacao e listagem).

Para reexecutar com relatorio de cobertura:

```bash
pytest --cov=app --cov-report=term-missing
```

---

## Parte 2 — Roteiro de testes manuais

### Teste A — Execucao local

**Objetivo:** confirmar que a API inicia e o Swagger esta acessivel.

**Pre-requisitos:** Python 3.11+, dependencias instaladas (`pip install -r requirements-dev.txt`).

**Passos:**
1. `uvicorn app.main:app --reload`
2. Abra `http://127.0.0.1:8000/docs` no navegador.

**Resultado esperado:** pagina Swagger UI carrega, listando os
endpoints `/health`, `/tarefas`, `/tarefas/{tarefa_id}`.

**Codigo HTTP esperado:** 200 (ao acessar `/docs`).

**Como identificar falha:** erro no terminal ao iniciar o Uvicorn, ou
pagina em branco/erro 500 no navegador.

**Evidencia:** print do Swagger UI aberto no navegador.

---

### Teste B — Cadastro

**Objetivo:** criar uma tarefa pelo Swagger e reconhecer o HTTP 201.

**Pre-requisitos:** Teste A concluido.

**Passos:**
1. No Swagger, expanda `POST /tarefas`.
2. Clique em "Try it out".
3. Preencha o corpo, por exemplo: `{"titulo": "Teste manual", "descricao": "Validacao do roteiro"}`.
4. Clique em "Execute".

**Resultado esperado:** corpo de resposta com `id`, `titulo`,
`descricao`, `concluida: false`, `criada_em` e `atualizada_em`
preenchidos.

**Codigo HTTP esperado:** `201`.

**Como identificar falha:** `422` (corpo invalido) ou `500` (erro
interno — verificar logs no terminal).

**Evidencia:** print da resposta do Swagger com o 201 visivel.

---

### Teste C — Consulta

**Objetivo:** consultar a tarefa criada e comparar os dados.

**Passos:**
1. Anote o `id` retornado no Teste B.
2. No Swagger, use `GET /tarefas/{tarefa_id}` com esse `id`.
3. Compare `titulo` e `descricao` com o que foi enviado no Teste B.

**Resultado esperado:** dados identicos aos enviados.

**Codigo HTTP esperado:** `200`.

**Como identificar falha:** `404` (id errado) ou dados diferentes do
enviado (bug de persistencia).

**Evidencia:** print da resposta do GET.

---

### Teste D — Atualizacao

**Objetivo:** modificar a tarefa e confirmar a persistencia da mudanca.

**Passos:**
1. Use `PUT /tarefas/{tarefa_id}` com o mesmo `id`, alterando `titulo` para `"Teste manual atualizado"` e `concluida` para `true`.
2. Execute.
3. Repita o `GET /tarefas/{tarefa_id}` do Teste C.

**Resultado esperado:** o `GET` reflete os novos valores, e
`atualizada_em` e maior que `criada_em`.

**Codigo HTTP esperado:** `200` no PUT.

**Como identificar falha:** `404` (id errado), `422` (corpo invalido),
ou o GET subsequente ainda mostrando os dados antigos.

**Evidencia:** print do PUT e do GET seguinte.

---

### Teste E — Exclusao

**Objetivo:** excluir a tarefa e confirmar que deixou de existir.

**Passos:**
1. Use `DELETE /tarefas/{tarefa_id}` com o mesmo `id`.
2. Em seguida, repita `GET /tarefas/{tarefa_id}`.

**Resultado esperado:** o DELETE retorna corpo vazio; o GET seguinte
retorna "Tarefa nao encontrada".

**Codigo HTTP esperado:** `204` no DELETE, `404` no GET seguinte.

**Como identificar falha:** DELETE retornando `404` (id ja nao
existia) ou o GET seguinte ainda retornando `200` (exclusao nao
efetivada).

**Evidencia:** print do DELETE (204) e do GET seguinte (404).

---

### Teste F — Persistencia

**Objetivo:** confirmar que os dados sobrevivem a um reinicio da
aplicacao.

**Passos:**
1. Cadastre uma nova tarefa (`POST /tarefas`).
2. Pare o Uvicorn (`Ctrl+C` no terminal).
3. Inicie novamente (`uvicorn app.main:app --reload`).
4. Liste as tarefas (`GET /tarefas`).

**Resultado esperado:** a tarefa cadastrada antes do reinicio ainda
aparece na listagem.

**Codigo HTTP esperado:** `200` na listagem, com a tarefa presente.

**Como identificar falha:** tarefa ausente apos o reinicio (indica
problema de configuracao do caminho do banco, ou uso de banco em
memoria por engano).

**Evidencia:** print da listagem antes e depois do reinicio.

---

### Teste G — Azure (acesso externo)

**Objetivo:** acessar a API publicada, a partir de outro dispositivo
ou rede (ex.: celular com dados moveis, fora da sua rede local).

**Pre-requisitos:** deploy na Azure concluido (ver `GUIA_AZURE.md`), IP
publico da VM conhecido.

**Passos:**
1. Em outro dispositivo/rede, acesse `http://<IP-PUBLICO-DA-VM>/health`.
2. Acesse tambem `http://<IP-PUBLICO-DA-VM>/docs`.

**Resultado esperado:** ambas as paginas respondem normalmente, iguais
ao ambiente local.

**Codigo HTTP esperado:** `200` em ambos.

**Como identificar falha:** timeout (NSG bloqueando a porta 80, ou
Nginx parado) ou erro de conexao recusada (Uvicorn/Nginx nao
configurados).

**Evidencia:** print do navegador/celular mostrando a URL publica e a
resposta.

---

### Teste H — Disponibilidade (health, systemd, logs)

**Objetivo:** validar a saude do servico na VM via terminal SSH.

**Passos:**
1. Conecte via SSH na VM.
2. Execute `sudo systemctl status api-tarefas`.
3. Execute `curl http://127.0.0.1:8000/health`.
4. Execute `sudo journalctl -u api-tarefas -n 50 --no-pager`.

**Resultado esperado:** status "active (running)"; health retorna
`{"status":"ok", ...}`; logs sem erros criticos recentes.

**Codigo HTTP esperado:** `200` no health check local.

**Como identificar falha:** status "failed" ou "inactive"; erros no
log (ex.: porta em uso, erro de permissao no diretorio de dados).

**Evidencia:** print do terminal SSH com os tres comandos e suas
saidas.

---

### Teste I — Reinicializacao da VM

**Objetivo:** confirmar que a aplicacao inicia automaticamente apos
reiniciar a VM, sem perder dados.

**Passos:**
1. Antes de reiniciar, cadastre uma tarefa de controle (anote o texto).
2. Na VM: `sudo reboot`.
3. Aguarde ~1 a 2 minutos e reconecte via SSH.
4. Execute `sudo systemctl status api-tarefas`.
5. Acesse `GET /tarefas` (local ou externamente) e confirme que a
   tarefa de controle ainda esta presente.

**Resultado esperado:** servico "active (running)" automaticamente
(sem precisar iniciar manualmente); tarefa de controle presente.

**Codigo HTTP esperado:** `200` na listagem, com a tarefa visivel.

**Como identificar falha:** servico nao inicia automaticamente
(verificar se `systemctl enable api-tarefas` foi executado); tarefa
ausente (problema no caminho persistente do banco).

**Evidencia:** print do `systemctl status` apos o reboot e da listagem
com a tarefa de controle.
