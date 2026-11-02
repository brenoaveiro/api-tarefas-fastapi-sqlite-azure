# CyberIncident API

**Plataforma de Gerenciamento de Incidentes de Segurança Cibernética**

API REST acadêmica, em Python/FastAPI com SQLite, que simula o registro de incidentes de uma central de operações de segurança (SOC). Hospedada em uma máquina virtual na Microsoft Azure.

- **Aplicação (dashboard):** http://20.80.10.214/
- **Swagger (documentação interativa):** http://20.80.10.214/docs
- **Health check:** http://20.80.10.214/health

> **Aviso:** todos os dados são **fictícios**. A conexão é **HTTP (sem HTTPS)**, pois não há domínio próprio para emitir certificado. A leitura (GET) é pública; a escrita (POST, PUT, PATCH, DELETE) é restrita por IP no Nginx.

## O que a aplicação faz

Permite registrar, consultar, classificar, acompanhar e gerenciar incidentes como phishing, malware, força bruta, acesso indevido, vazamento de dados e anomalias de rede. Cada incidente tem severidade (`baixa`, `media`, `alta`, `critica`), status (`aberto`, `em_analise`, `contido`, `resolvido`), IP de origem opcional, ativo afetado e datas em UTC. A aplicação **não** detecta ameaças de verdade.

| Método e rota | Função |
|---|---|
| `GET /` | Dashboard SOC (cartões, gráfico por severidade e tabela de incidentes) |
| `GET /health` | Disponibilidade da API e do SQLite |
| `GET /incidentes` | Lista com paginação e filtros (`severidade`, `status`, `categoria`) |
| `GET /incidentes/estatisticas` | Contagens reais por status, severidade e categoria |
| `GET /incidentes/{id}` | Consulta um incidente |
| `POST /incidentes` | Cadastra (status inicial `aberto`) |
| `PUT /incidentes/{id}` | Atualiza todos os campos |
| `PATCH /incidentes/{id}/status` | Altera somente o status (respeita o fluxo de tratamento) |
| `DELETE /incidentes/{id}` | Exclui um incidente de demonstração |

O status segue o fluxo `aberto → em_analise → contido/resolvido`; resolvido pode ser reaberto. Transições fora do fluxo retornam 422. `resolvido_em` é preenchido ao resolver e limpo ao reabrir.

## Tecnologias

Python 3 · FastAPI · Pydantic · SQLAlchemy · SQLite · Uvicorn · Nginx · systemd · HTML/CSS/JavaScript (sem frameworks) · Swagger UI (servido localmente) · Pytest · Git/GitHub · Microsoft Azure (VM Ubuntu 24.04).

## Estrutura do projeto

```text
app/            API (main, models, schemas, crud, enums) e interface (static/: dashboard e tema do Swagger)
deploy/         install.sh, deploy.sh, backup.sh, configuração do Nginx e do systemd
docs/           relatório técnico, guias, roteiro de apresentação, diagramas e evidências
scripts/        testar_producao.sh e gerar_relatorio.py
tests/          55 testes automatizados (pytest)
```

## Executar localmente

```bash
python -m venv .venv
.venv\Scripts\activate                 # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env                 # Linux/macOS: cp .env.example .env
uvicorn app.main:app --reload
```

Abra http://127.0.0.1:8000/ (dashboard) e http://127.0.0.1:8000/docs (Swagger). O banco local fica em `data/` (ignorado pelo Git). Para ver dados de exemplo, defina `SEED_DEMO_DATA=true` no `.env`.

## Testes

```bash
python -m pytest -q                                              # 55 testes locais
./scripts/testar_producao.sh <IP-PUBLICO> <chave-ssh>            # 30 verificações na VM
```

Detalhes em [`docs/GUIA_TESTES.md`](docs/GUIA_TESTES.md).

## Infraestrutura Azure (valores reais)

| Item | Valor |
|---|---|
| Região | North Central US |
| Resource Group | `GS_Cloud_API` |
| Máquina virtual | `GS-Cloud-API-VM` — `Standard_B2ats_v2` (2 vCPU, 1 GiB) — Ubuntu Server 24.04 LTS |
| Disco | `GS_Cloud_API_Disk` — Standard SSD LRS, 32 GiB (Managed Disk) |
| Rede | `GS_Cloud_API_VNet` / `GS_Cloud_API_Subnet`, IP público Standard estático, NSG `GS_Cloud_API_NSG` |
| Banco | SQLite em `/var/lib/api-tarefas/tarefas.db` (disco persistente) |
| Serviços | Nginx (porta 80) → Uvicorn (`127.0.0.1:8000`) gerenciado pelo systemd (`api-tarefas`) |

O detalhamento (por que a `Standard_B1s` não foi usada, comandos, custos e atualização para a CyberIncident API) está em [`docs/DEPLOY_AZURE_REAL.md`](docs/DEPLOY_AZURE_REAL.md).

## Segurança

- NSG: SSH só do IP do administrador; apenas a porta 80 pública; a porta 8000 nunca é exposta.
- Nginx: escrita só para IPs autorizados (arquivo local da VM, fora do Git); os demais recebem 403.
- Consultas parametrizadas (ORM), `textContent` no dashboard e CSP contra XSS, sem CORS aberto, erros 500 sem detalhes.
- `.env`, banco, chaves e backups não são versionados (`.gitignore`).
- **Limitações:** sem HTTPS, sem autenticação de usuários, SQLite para baixa concorrência e VM com 1 GiB de RAM.

## Atualização e backup

`sudo /opt/api-tarefas/deploy/deploy.sh` (na VM) faz backup consistente do SQLite, **aborta se o backup falhar**, atualiza o código, a unidade systemd e reinicia o serviço. A criação da tabela `incidentes` é não destrutiva; a tabela antiga `tarefas` é preservada.

## Documentação

[Relatório técnico](docs/RELATORIO_TECNICO.md) · [Relatório Word](docs/relatorio-final.docx) · [Relatório PDF](docs/relatorio-final.pdf) · [Guia Azure](docs/GUIA_AZURE.md) · [Guia de testes](docs/GUIA_TESTES.md) · [Guia de evidências](docs/GUIA_PRINTS.md) · [Apresentação](docs/APRESENTACAO.md) · [Diagramas](docs/diagramas/)

## Licença

MIT — veja [LICENSE](LICENSE).
