# Guia de Testes — CyberIncident API

## 1. Testes automatizados locais (pytest)

Usam um banco SQLite temporário e isolado (veja `tests/conftest.py`): nunca tocam o banco real.

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (no Linux: source .venv/bin/activate)
pip install -r requirements-dev.txt
python -m pytest -q
```

Resultado esperado: **96 aprovados, sem avisos** — `tests/test_incidentes.py` (40), `tests/test_install_env.py` (15) e `tests/test_entrega.py` (41).

| Grupo | O que valida |
|---|---|
| Inicialização e health | `/health` 200 e comportamento degradado (503) quando o banco falha, sem vazar detalhes |
| CRUD | POST 201, GET por ID e 404, PUT, DELETE 204 |
| Listagem | paginação, filtros por severidade, status e categoria, ordem do mais recente |
| Status | transições permitidas, 422 nas inválidas, `resolvido_em` ao resolver e limpo ao reabrir |
| Validações | severidade, status, categoria e IP inválidos; campos obrigatórios; IPv6; campo vazio |
| Estatísticas | banco vazio, por severidade, por status e por categoria; rota não confundida com o ID |
| Persistência e migração | dados após reabrir o banco; tabela antiga `tarefas` preservada; migração repetível; restrições `CHECK` |
| Interface | dashboard, arquivos CSS/JS, Swagger sem CDN, OpenAPI, ausência de `innerHTML` |
| Segurança | XSS armazenado como texto, SQL injection, erro 500 sem vazamento, CORS fechado |
| Entrega e reprodutibilidade | presença e integridade dos arquivos (Swagger e licença), dependências fixadas, sintaxe dos scripts, script de produção sem contagem de linhas, `.gitignore` |
| Nginx, HTTPS e CI | bloqueio de escrita nas duas portas, desafio ACME, TLS 1.2/1.3, ausência de HSTS e de redirecionamento forçado, script `https_ip.sh` e workflow de CI |

Para rodar apenas um grupo: `python -m pytest tests/test_incidentes.py -k estatisticas -q`. Análise estática e auditoria de dependências: `python -m pyflakes app scripts` e `python -m pip_audit -r requirements.txt` (resultado atual: sem problemas e sem vulnerabilidades conhecidas).

## 2. Integração contínua

O workflow `.github/workflows/ci.yml` roda a cada push em `main`: instala as dependências em ambiente limpo, confere a presença de 16 arquivos essenciais, valida a sintaxe dos scripts e executa o pytest. Não usa credenciais da Azure nem faz deploy.

## 3. Testes na URL pública (Azure)

O script executa **58 verificações** contra a VM: interface e arquivos do Swagger, estatísticas coerentes, CRUD completo e transições, validações (422/404), reinício do serviço e persistência, porta 8000 fechada, bloqueio de escrita por IP não autorizado (HTTP e HTTPS), permissões do banco, HTTPS (certificado verificado, emissor Let's Encrypt, IP no certificado, validade, timer e hook de renovação) e integridade do SQLite (tabelas via `sqlite_master`, `journal_mode`, `integrity_check`). Deve ser rodado **do IP liberado para escrita**.

```bash
REQUIRE_HTTPS=1 ./scripts/testar_producao.sh 20.80.10.214 ~/.ssh/id_ed25519_apitarefas | tee docs/evidencias/testes-producao-$(date +%Y%m%d-%H%M%S).txt
```

- Cada verificação conta uma vez como `[OK]` ou `[FALHA]`; erros de SSH, de SQLite e de leitura de JSON também são falhas. O código de saída é 0 somente sem falhas.
- Se o POST falhar, o bloco de CRUD dependente não é executado e a falha é registrada.
- O incidente criado pelo teste é removido ao final (inclusive se o script for interrompido); nenhum outro registro é tocado.
- Sem `REQUIRE_HTTPS=1`, a ausência de HTTPS vira `[N/A]` em vez de falha.

Resultado real (2026-11-02): **58 verificações, 58 aprovadas, 0 falhas, código de saída 0** (`docs/evidencias/testes-producao-20261102-180113.txt`). Um teste negativo com chave SSH inválida de propósito produziu **13 falhas contabilizadas e código de saída 1** (`docs/evidencias/teste-negativo-script-ssh-invalido-*.txt`). O log da versão anterior do script foi mantido em `docs/evidencias/testes-producao-20261102-script-v1-historico.txt`.

## 4. Teste manual rápido

```bash
curl https://20.80.10.214/health
curl https://20.80.10.214/incidentes/estatisticas
curl -X POST https://20.80.10.214/incidentes -H "Content-Type: application/json" \
  -d '{"titulo":"[TESTE] Exemplo","descricao":"Registro fictício","categoria":"phishing","severidade":"media","ativo_afetado":"srv-01"}'
```

O POST só funciona do IP autorizado; de outros IPs retorna 403. Use apenas dados fictícios.

## 5. Persistência

1. Cadastre um incidente e anote o `id`.
2. `ssh azureuser@<IP> "sudo systemctl restart api-tarefas"`.
3. Consulte `GET /incidentes/<id>`: os dados devem ser idênticos (o arquivo SQLite fica no disco gerenciado).
