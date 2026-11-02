# API de Gerenciamento de Tarefas na Azure

> Projeto academico: API REST em Python/FastAPI, com persistencia em
> SQLite, preparada para hospedagem em uma Azure Virtual Machine Ubuntu
> com Nginx + systemd.

## 1. Descricao do projeto

Esta API permite cadastrar, listar, consultar, atualizar e excluir
tarefas (CRUD completo), com validacao de dados, tratamento de erros
HTTP, documentacao automatica (Swagger/OpenAPI) e persistencia em
arquivo SQLite. O projeto foi desenvolvido para demonstrar, de forma
pratica e reproduzivel, o ciclo completo de uma API hospedada em nuvem:
desenvolvimento → testes → controle de versao → publicacao no GitHub →
implantacao em uma VM na Microsoft Azure.

## 2. Objetivo academico

Demonstrar, com evidencias reais (codigo executavel, testes aprovados e
capturas de tela), a construcao e a implantacao de uma API REST em
ambiente de nuvem, cobrindo desenvolvimento backend, persistencia de
dados, infraestrutura como VM, seguranca basica de rede/aplicacao e
documentacao tecnica.

## 3. Tecnologias utilizadas

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.13 |
| Framework de API | FastAPI |
| Validacao | Pydantic |
| ORM / persistencia | SQLAlchemy |
| Banco de dados | SQLite |
| Servidor ASGI | Uvicorn |
| Proxy reverso | Nginx |
| Maquina virtual | Azure Virtual Machine (Ubuntu Server LTS, SKU `Standard_B1s`) |
| Gerenciamento de processo | systemd |
| Testes | Pytest + HTTPX |
| Documentacao de API | Swagger / OpenAPI (gerado automaticamente pelo FastAPI) |
| Diagramas | Mermaid |
| Controle de versao | Git + GitHub |

## 4. Arquitetura

Veja os diagramas completos em [`docs/diagramas/`](docs/diagramas/).
Resumo do fluxo:

```
Usuario -> Internet -> IP publico -> NSG -> VM Ubuntu -> Nginx -> Uvicorn/FastAPI -> SQLite (disco persistente)
```

## 5. Pre-requisitos

- Python 3.11 ou superior.
- Git.
- (Para deploy) Conta Microsoft Azure com assinatura ativa e acesso SSH.

## 6. Instalacao local

```bash
git clone https://github.com/<seu-usuario>/api-tarefas-fastapi-sqlite-azure.git
cd api-tarefas-fastapi-sqlite-azure
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

pip install -r requirements-dev.txt
cp .env.example .env
```

## 7. Configuracao

Edite o arquivo `.env` (nunca o `.env.example`) se precisar alterar o
caminho do banco de dados ou outros limites. Veja todas as variaveis em
[`.env.example`](.env.example).

## 8. Inicializando a aplicacao

```bash
uvicorn app.main:app --reload
```

A aplicacao cria o banco de dados e as tabelas automaticamente na
primeira execucao. Acesse a documentacao interativa em:

- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

## 9. Endpoints

| Metodo | Caminho | Descricao | Status de sucesso |
|---|---|---|---|
| GET | `/health` | Saude da aplicacao e do banco | 200 |
| GET | `/tarefas` | Lista tarefas (paginado: `skip`, `limit`) | 200 |
| GET | `/tarefas/{id}` | Consulta uma tarefa | 200 / 404 |
| POST | `/tarefas` | Cria uma tarefa | 201 |
| PUT | `/tarefas/{id}` | Atualiza uma tarefa | 200 / 404 |
| DELETE | `/tarefas/{id}` | Exclui uma tarefa | 204 / 404 |

## 10. Exemplos de requisicoes

**Criar uma tarefa:**

```bash
curl -X POST http://127.0.0.1:8000/tarefas \
  -H "Content-Type: application/json" \
  -d '{"titulo": "Estudar para a prova", "descricao": "Capitulo 4"}'
```

**Resposta (HTTP 201):**

```json
{
  "titulo": "Estudar para a prova",
  "descricao": "Capitulo 4",
  "id": 1,
  "concluida": false,
  "criada_em": "2026-11-01T10:00:00.000000",
  "atualizada_em": "2026-11-01T10:00:00.000000"
}
```

**Listar tarefas (paginado):**

```bash
curl "http://127.0.0.1:8000/tarefas?skip=0&limit=10"
```

## 11. Execucao dos testes

```bash
pytest
```

Resultado obtido durante o desenvolvimento deste projeto: **19
testes aprovados** (0 falhas). Veja detalhes em
[`docs/GUIA_TESTES.md`](docs/GUIA_TESTES.md).

## 12. Banco de dados

SQLite, com arquivo persistente configuravel via `DATABASE_URL`. Veja a
explicacao completa (o que e, por que foi escolhido, limitacoes, e
diferenca entre disco persistente/temporario/gerenciado) no
[Capitulo 6 do relatorio tecnico](docs/RELATORIO_TECNICO.md#capitulo-6--banco-de-dados).

## 13. Deploy na Azure

Guia completo, com custos estimados, seguranca de rede e scripts de
instalacao, em [`docs/GUIA_AZURE.md`](docs/GUIA_AZURE.md). Scripts em
[`deploy/`](deploy/).

## 14. Diagramas

Veja [`docs/diagramas/`](docs/diagramas/) (5 diagramas Mermaid:
arquitetura Azure, fluxo HTTP, modelo ER, processo de deploy e processo
de testes).

## 15. Seguranca

- Sem autenticacao complexa (fora do escopo academico). Medida simples
  proposta para proteger escrita na internet: ver
  [Capitulo 12 do relatorio tecnico](docs/RELATORIO_TECNICO.md#capitulo-12--seguranca-e-limitacoes).
- Uvicorn nunca exposto diretamente; apenas via Nginx.
- Porta 22 (SSH) restrita ao IP do administrador via NSG.
- Sem segredos no repositorio (`.env`, chaves e bancos reais estao no
  `.gitignore`).

## 16. Limitacoes

- SQLite nao e um banco de producao para alta concorrencia/escala.
- Sem autenticacao/autorizacao de usuarios.
- SKU `Standard_B1s` tem recursos minimos (1 vCPU, 1 GiB RAM) — adequada
  apenas para demonstracao academica de baixo trafego.
- HTTPS valido requer um dominio proprio apontado para a VM (nao
  incluso por padrao).

## 17. Link publico da aplicacao

`[PENDENTE — preencher com a URL publica apos o deploy na Azure ser
validado]`

## 18. Documentacao tecnica

Veja a pasta [`docs/`](docs/): relatorio tecnico completo, guia Azure,
guia de testes, guia de screenshots e roteiro de apresentacao.

## 19. Manutencao

- Atualizacoes de codigo na VM: `sudo ./deploy/deploy.sh` (faz backup,
  atualiza o codigo e reinicia o servico).
- Backup do banco: `sudo ./deploy/backup.sh` (backup consistente via
  `sqlite3 .backup`).
- Logs do servico: `journalctl -u api-tarefas -f`.

## Licenca

Este projeto esta licenciado sob a licenca MIT — veja [`LICENSE`](LICENSE).
