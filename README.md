# CyberIncident API

[![CI](https://github.com/brenoaveiro/api-tarefas-fastapi-sqlite-azure/actions/workflows/ci.yml/badge.svg)](https://github.com/brenoaveiro/api-tarefas-fastapi-sqlite-azure/actions/workflows/ci.yml)

**Plataforma de Gerenciamento de Incidentes de Segurança Cibernética**

API REST acadêmica, em Python/FastAPI com SQLite, que simula o registro de incidentes de uma central de operações de segurança (SOC). Hospedada em uma máquina virtual na Microsoft Azure.

> **Documento oficial do trabalho:** [GS_CloudSec_BrenoAveiro.pdf](docs/GS_CloudSec_BrenoAveiro.pdf) (Global Solution — Cloud Security). É o relatório oficial e a única documentação da entrega; a pasta `docs/` contém apenas ele.

> **Status da hospedagem:** a aplicação ficou publicada na Azure (VM Ubuntu com Nginx, HTTPS e SQLite) e foi **validada e documentada**; depois disso, **todos os recursos do Resource Group `GS_Cloud_API` foram excluídos** para encerrar qualquer custo. Por isso os endereços `https://20.80.10.214/` citados nos documentos **não respondem mais**. As evidências reais (capturas, resultados dos testes e diagramas) estão no relatório oficial. O projeto continua executável localmente (veja abaixo).

> **Avisos:** todos os dados são **fictícios**. Durante a hospedagem, o HTTPS usava um certificado Let's Encrypt emitido para o **endereço IP** (validade de cerca de 6 dias, renovação automática). A leitura (GET) era pública; a escrita (POST, PUT, PATCH, DELETE) era restrita por IP no Nginx, pois a API não tem autenticação de usuários.

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

Python 3.12 · FastAPI 0.162 · Starlette 1.10 · Pydantic 2.14 · SQLAlchemy 2.0 · SQLite · Uvicorn · Nginx · systemd · Certbot (Let's Encrypt) · HTML/CSS/JavaScript sem frameworks · Swagger UI (servido localmente) · Pytest · GitHub Actions · Microsoft Azure (VM Ubuntu 24.04).

## Estrutura do projeto

```text
app/            API (main, models, schemas, crud, enums) e interface (static/: dashboard, tema e Swagger UI local)
deploy/         install.sh, deploy.sh, backup.sh, https_ip.sh, configuração do Nginx (HTTP e HTTPS) e do systemd
docs/           relatório oficial (GS_CloudSec_BrenoAveiro.pdf)
scripts/        testar_producao.sh
tests/          96 testes automatizados (pytest)
.github/        workflow de integração contínua
```

## Executar localmente (ambiente limpo)

```bash
python -m venv .venv
.venv\Scripts\activate                 # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env                 # Linux/macOS: cp .env.example .env
uvicorn app.main:app --reload
```

Abra http://127.0.0.1:8000/ (dashboard) e http://127.0.0.1:8000/docs (Swagger). O banco local fica em `data/` (ignorado pelo Git). Para ver dados de exemplo, defina `SEED_DEMO_DATA=true` no `.env`. Todos os arquivos necessários, inclusive os do Swagger UI, estão no repositório: não há download em tempo de execução.

## Testes

```bash
python -m pytest -q                                                    # 96 testes locais
REQUIRE_HTTPS=1 ./scripts/testar_producao.sh <IP-PUBLICO> <chave-ssh>   # 58 verificações na VM
```

A integração contínua (GitHub Actions) instala as dependências em ambiente limpo, confere os arquivos necessários e executa a suíte a cada envio.

## Infraestrutura Azure (valores reais)

| Item | Valor |
|---|---|
| Região | North Central US |
| Resource Group | `GS_Cloud_API` |
| Máquina virtual | `GS-Cloud-API-VM` — `Standard_B2ats_v2` (2 vCPU, 1 GiB) — Ubuntu Server 24.04 LTS |
| Disco | `GS_Cloud_API_Disk` — Standard SSD LRS, 32 GiB (Managed Disk) |
| Rede | `GS_Cloud_API_VNet` / `GS_Cloud_API_Subnet`, IP público Standard estático, NSG `GS_Cloud_API_NSG` (22 só do administrador, 80 e 443 públicas) |
| Banco | SQLite em `/var/lib/api-tarefas/tarefas.db` (disco persistente; tabelas `incidentes` e a antiga `tarefas`) |
| Serviços | Nginx (80 e 443) → Uvicorn (`127.0.0.1:8000`) gerenciado pelo systemd (`api-tarefas`) |

O detalhamento (SKU, comandos, HTTPS, custos e atualização) está no relatório oficial.

## Segurança

- NSG: SSH só do IP do administrador; apenas as portas 80 e 443 públicas; a porta 8000 nunca é exposta.
- Nginx: escrita só para IPs autorizados (arquivo local da VM, fora do Git), nas duas portas; os demais recebem 403.
- HTTPS com certificado Let's Encrypt para o IP, TLS 1.2/1.3 e renovação automática (timer systemd + hook de recarga do Nginx).
- Consultas parametrizadas (ORM), `textContent` e CSP no dashboard, sem CORS aberto, erros 500 sem detalhes, dependências sem vulnerabilidades conhecidas (`pip-audit`).
- `.env`, banco, chaves e backups não são versionados (`.gitignore`).
- **Limitações:** sem autenticação de usuários, SQLite para baixa concorrência, VM única com 1 GiB de RAM e certificado de curta duração (ver o relatório).

## Atualização e backup

`sudo /opt/api-tarefas/deploy/deploy.sh` (na VM) faz backup consistente do SQLite, **aborta se o backup falhar**, atualiza o código, a unidade systemd e a configuração do Nginx (com `nginx -t` e restauração automática) e reinicia o serviço. A tabela `incidentes` é criada sem apagar dados; a tabela antiga `tarefas` é preservada. O HTTPS é configurado por `sudo ./deploy/https_ip.sh <IP>`.

## Documentação

[**Relatório oficial (PDF)**](docs/GS_CloudSec_BrenoAveiro.pdf)

## Licença

MIT — veja [LICENSE](LICENSE). O Swagger UI (Apache 2.0) acompanha sua licença em `app/static/swagger/`.
