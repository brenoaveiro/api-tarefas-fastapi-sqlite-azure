# Guia de Testes — CyberIncident API

## 1. Testes automatizados locais (pytest)

Usam um banco SQLite temporário e isolado (veja `tests/conftest.py`): nunca tocam o banco real.

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (no Linux: source .venv/bin/activate)
pip install -r requirements-dev.txt
python -m pytest -q
```

Resultado esperado: **55 aprovados** (40 em `tests/test_incidentes.py` e 15 em `tests/test_install_env.py`) e 1 aviso de depreciação de uma dependência (não é erro).

| Grupo | O que valida |
|---|---|
| Inicialização e health | `/health` 200 e comportamento degradado (503) quando o banco falha, sem vazar detalhes |
| CRUD | POST 201, GET por ID e 404, PUT, DELETE 204 |
| Listagem | paginação, filtros por severidade, status e categoria, ordem do mais recente |
| Status | transições permitidas, 422 nas inválidas, `resolvido_em` ao resolver e limpo ao reabrir |
| Validações | severidade, status, categoria e IP inválidos; campos obrigatórios; IPv6; campo vazio |
| Estatísticas | banco vazio, por severidade, por status e por categoria; rota não confundida com o ID |
| Persistência e migração | dados após reabrir o banco; tabela antiga `tarefas` preservada; migração repetível |
| Interface | dashboard, arquivos CSS/JS, Swagger sem CDN, OpenAPI, ausência de `innerHTML` |
| Segurança | XSS armazenado como texto, SQL injection, erro 500 sem vazamento, CORS fechado |
| Regressão de infraestrutura | Nginx com bloqueio de escrita, Uvicorn só em 127.0.0.1, systemd e `.gitignore` |

Para rodar apenas um grupo: `python -m pytest tests/test_incidentes.py -k estatisticas -q`.

## 2. Testes na URL pública (Azure)

O script abaixo executa 30 verificações contra a VM, incluindo reinício do serviço e a prova de que a escrita de IPs não autorizados é bloqueada. Deve ser rodado **do IP liberado para escrita**.

```bash
./scripts/testar_producao.sh 20.80.10.214 ~/.ssh/id_ed25519_apitarefas
```

Resultado real (2026-11-02): **30 aprovados, 0 falhas** — arquivo `docs/evidencias/testes-producao.txt`.

## 3. Teste manual rápido

```bash
curl http://20.80.10.214/health
curl http://20.80.10.214/incidentes/estatisticas
curl -X POST http://20.80.10.214/incidentes -H "Content-Type: application/json" \
  -d '{"titulo":"[TESTE] Exemplo","descricao":"Registro fictício","categoria":"phishing","severidade":"media","ativo_afetado":"srv-01"}'
```

O POST só funciona do IP autorizado; de outros IPs retorna 403. Use apenas dados fictícios.

## 4. Persistência

1. Cadastre um incidente e anote o `id`.
2. `ssh azureuser@<IP> "sudo systemctl restart api-tarefas"`.
3. Consulte `GET /incidentes/<id>`: os dados devem ser idênticos (o arquivo SQLite fica no disco gerenciado).
