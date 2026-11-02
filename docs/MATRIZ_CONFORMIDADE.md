# Matriz de conformidade — exigências do professor

Cada exigência está ligada à implementação, ao arquivo de código, ao teste, à evidência (figura), à seção do relatório (`docs/RELATORIO_TECNICO.md`) e ao resultado da verificação. Status: **Atendido** só com evidência correspondente.

| # | Exigência | Implementação | Código | Teste | Evidência | Seção | Resultado da verificação | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | API básica funcional | API REST de incidentes (CRUD, PATCH de status, estatísticas, health) com dashboard | `app/main.py`, `app/crud.py`, `app/schemas.py`, `app/enums.py` | `tests/test_incidentes.py` (40) | Fig. 07 a 13 | 5 | 96 testes locais e 58 verificações em produção aprovados; CRUD, 201/200/204/404/422 conferidos | Atendido |
| 2 | Banco SQLite | Tabela `incidentes` (constraints, índices, WAL); tabela antiga `tarefas` preservada | `app/models.py`, `app/database.py` | persistência, migração repetível, `CHECK`, estatísticas | Fig. 15 e 16 | 6 | `integrity_check ok`, WAL, tabelas conferidas em `sqlite_master`, dados após reinício | Atendido |
| 3 | Hospedagem de ponta a ponta | VM Azure com Nginx (80/443), Uvicorn e systemd, acessível pela internet | `deploy/install.sh`, `deploy/deploy.sh`, `deploy/nginx/*.conf`, `deploy/systemd/api-tarefas.service` | `tests/test_entrega.py` (Nginx/systemd); `scripts/testar_producao.sh` | Fig. 01 a 06, 14 | 7 e 8 | https://20.80.10.214/ responde 200 (certificado verificado); serviços ativos | Atendido |
| 4 | Link do repositório GitHub | Repositório público com código, docs e CI | `.github/workflows/ci.yml` | CI (GitHub Actions) | Fig. 17 | 1 e 8 | https://github.com/brenoaveiro/api-tarefas-fastapi-sqlite-azure; CI `success` | Atendido |
| 5 | Documentação completa | README, relatório (MD, Word, PDF), guias, defesa oral, auditoria, matriz | `README.md`, `docs/*.md` | checagem de assets e referências | Relatório em `07_Relatorio` | todas | Documentos coerentes com o código e a VM; PDF e Word renderizados e inspecionados | Atendido |
| 6 | Esquemas visuais da arquitetura | 6 diagramas Mermaid (arquitetura, HTTP, ER, cadastro, deploy, testes) | `docs/diagramas/*.md` e `docs/diagramas/png/` | — (revisão visual) | Diagramas 1 a 6 | 12 | Coerentes com o código e a infraestrutura reais (HTTPS, NSG 80/443, CI) | Atendido |
| 7 | Documento Word ou PDF detalhado | `relatorio-final.docx` e `.pdf` (A4, Arial 11, preto, justificado, sem cabeçalho/rodapé) | `scripts/gerar_relatorio.py`, `docs/RELATORIO_TECNICO.md` | verificação de formatação via Word (cabeçalho/rodapé vazios) | — | todas | Gerados a partir de um texto-fonte único; páginas inspecionadas | Atendido |
| 8 | Prints reais de tela | 18 figuras reais: Portal, navegador e janelas de console | scripts de captura (Playwright e janela do console) | — (inspeção visual individual) | Fig. 01 a 18 | 11 | 18 de 18 válidas, legíveis, sem dados sensíveis; mascaramento declarado | Atendido |
| 9 | Explicar os componentes na nuvem | Texto sobre Resource Group, VM, SKU, disco, VNet, subnet, NSG, IP, custos | — | — | Fig. 01 a 06; Diagrama 1 | 7 e 13 | Valores lidos da Azure (CLI e Portal) | Atendido |
| 10 | Explicar o armazenamento | Managed Disk Standard SSD LRS 32 GiB; SQLite no disco; WAL; backup | `app/database.py`, `deploy/backup.sh` | persistência e migração | Fig. 04, 15 e 16 | 6 e 7 | Disco vinculado à VM; dados sobrevivem ao reinício | Atendido |
| 11 | Explicar a VM e a SKU | `Standard_B2ats_v2`: 2 vCPU, 1 GiB, série B (*burstable*); por que não a B1s | — | — | Fig. 02 e 03 | 7 | Portal confirma a SKU atual (Current size) e a tabela de tamanhos | Atendido |
| 12 | Explicar a linguagem de programação | Python 3.12 (e FastAPI, Pydantic, SQLAlchemy) com justificativa | `app/` | — | — | 3 | Versões fixadas em `requirements.txt` e conferidas na VM | Atendido |

## Itens adicionais de qualidade

| Item | Resultado | Evidência |
|---|---|---|
| Reprodutibilidade em ambiente limpo | Aprovado (ver `docs/AUDITORIA_FINAL.md`, seção de reprodução) | testes e `pip install` a partir do pacote extraído |
| HTTPS | Certificado Let's Encrypt para o IP, válido, renovação automática comprovada | `docs/DEPLOY_AZURE_REAL.md`, seção 6; log de produção |
| Vulnerabilidades de dependências | Nenhuma conhecida (`pip-audit`) | `requirements.txt` fixado |
| Script de produção | 58 verificações; falhas contabilizadas e código de saída correto (teste negativo: 13 falhas, saída 1) | `docs/evidencias/` |
| Segredos | Nenhum no repositório ou no pacote | varredura de texto e `.gitignore` |
