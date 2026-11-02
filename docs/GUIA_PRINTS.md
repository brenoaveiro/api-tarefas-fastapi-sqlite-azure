# Guia de Screenshots — Evidencias para o Relatorio

Todas as capturas abaixo sao de telas **reais** (seu VS Code, seu
navegador, seu terminal, seu portal Azure, seu GitHub). Nenhuma imagem
simulada deve substituir estas evidencias. Salve os arquivos em
`docs/screenshots/` com os nomes sugeridos.

---

### 1. Estrutura de pastas no VS Code

- **Tela:** VS Code, painel "Explorer" (barra lateral esquerda).
- **Onde clicar:** abra a pasta raiz do projeto `api-tarefas-azure`.
- **O que deve aparecer:** arvore completa (`app/`, `tests/`, `deploy/`, `docs/`, `scripts/`, `README.md`, etc.), expandida.
- **O que nao deve aparecer:** nenhum arquivo `.env` real ou credenciais abertas no editor.
- **Arquivo:** `01-estrutura-pastas.png`
- **Legenda sugerida:** "Figura 01 — Estrutura de pastas do projeto no VS Code."
- **Capitulo:** 5 (Desenvolvimento da API) / 10 (Evidencias).

### 2. Arquivo principal da API

- **Tela:** VS Code com `app/main.py` aberto.
- **O que deve aparecer:** os endpoints (`/health`, `/tarefas`, etc.) visiveis no editor.
- **Arquivo:** `02-main-py.png`
- **Legenda:** "Figura 02 — Codigo do arquivo app/main.py."
- **Capitulo:** 5.

### 3. Definicao dos modelos

- **Tela:** VS Code com `app/models.py` aberto.
- **O que deve aparecer:** a classe `Tarefa` e suas colunas.
- **Arquivo:** `03-models-py.png`
- **Legenda:** "Figura 03 — Modelo de dados (SQLAlchemy) da tarefa."
- **Capitulo:** 6 (Banco de dados).

### 4. Swagger com todos os endpoints

- **Tela:** navegador em `http://127.0.0.1:8000/docs`.
- **Comando antes:** `uvicorn app.main:app --reload`.
- **O que deve aparecer:** todos os endpoints listados (GET/POST/PUT/DELETE em `/tarefas`, GET em `/health`).
- **Arquivo:** `04-swagger-geral.png`
- **Legenda:** "Figura 04 — Documentacao interativa (Swagger UI) com todos os endpoints."
- **Capitulo:** 5 / 9 (Testes).

### 5. Requisicao POST funcionando

- **Tela:** Swagger, endpoint `POST /tarefas` apos "Execute".
- **O que deve aparecer:** corpo da requisicao enviado e resposta com **HTTP 201** e o JSON criado.
- **Arquivo:** `05-post-tarefa.png`
- **Legenda:** "Figura 05 — Cadastro de tarefa via POST (HTTP 201)."
- **Capitulo:** 9.

### 6. Requisicao GET funcionando

- **Tela:** Swagger, endpoint `GET /tarefas/{tarefa_id}`.
- **O que deve aparecer:** resposta **HTTP 200** com os dados da tarefa.
- **Arquivo:** `06-get-tarefa.png`
- **Legenda:** "Figura 06 — Consulta de tarefa via GET (HTTP 200)."
- **Capitulo:** 9.

### 7. Requisicao PUT funcionando

- **Tela:** Swagger, endpoint `PUT /tarefas/{tarefa_id}`.
- **O que deve aparecer:** corpo enviado com alteracoes e resposta **HTTP 200** refletindo-as.
- **Arquivo:** `07-put-tarefa.png`
- **Legenda:** "Figura 07 — Atualizacao de tarefa via PUT (HTTP 200)."
- **Capitulo:** 9.

### 8. Requisicao DELETE funcionando

- **Tela:** Swagger, endpoint `DELETE /tarefas/{tarefa_id}`.
- **O que deve aparecer:** resposta **HTTP 204** (corpo vazio).
- **Arquivo:** `08-delete-tarefa.png`
- **Legenda:** "Figura 08 — Exclusao de tarefa via DELETE (HTTP 204)."
- **Capitulo:** 9.

### 9. SQLite mostrando registros persistidos

- **Tela:** terminal, usando `sqlite3` ou extensao "SQLite Viewer" do VS Code.
- **Comando:** `sqlite3 data/tarefas.db "SELECT * FROM tarefas;"`
- **O que deve aparecer:** linhas da tabela `tarefas` com dados reais cadastrados nos testes manuais.
- **O que nao deve aparecer:** dados sensiveis (nao ha neste projeto, mas evite titulos/descricoes com informacoes pessoais).
- **Arquivo:** `09-sqlite-registros.png`
- **Legenda:** "Figura 09 — Registros persistidos no banco SQLite."
- **Capitulo:** 6 / 9.

### 10. Testes automatizados aprovados

- **Tela:** terminal apos `pytest`.
- **O que deve aparecer:** a linha final `19 passed` (ou o numero real obtido na sua execucao).
- **Arquivo:** `10-pytest-aprovado.png`
- **Legenda:** "Figura 10 — Execucao da suite de testes automatizados (Pytest)."
- **Capitulo:** 9.

### 11. GitHub mostrando o repositorio

- **Tela:** navegador, pagina do repositorio no GitHub.
- **O que deve aparecer:** nome do repositorio, arquivos na raiz, README renderizado.
- **Arquivo:** `11-github-repo.png`
- **Legenda:** "Figura 11 — Repositorio publicado no GitHub."
- **Capitulo:** 8 (Implantacao).

### 12. Azure — Resource Group

- **Tela:** portal Azure, pagina do Resource Group `GS_Cloud_API`.
- **O que deve aparecer:** nome do grupo, lista de recursos associados (VM, disco, IP, rede).
- **O que nao deve aparecer:** nome completo da assinatura/ID de cobranca em destaque (pode recortar se preferir).
- **Arquivo:** `12-azure-resource-group.png`
- **Legenda:** "Figura 12 — Resource Group criado na Azure."
- **Capitulo:** 7 (Infraestrutura Azure) / 10.

### 13. Azure — Virtual Machine

- **Tela:** portal Azure, pagina "Overview" da VM.
- **O que deve aparecer:** nome da VM, status "Running", IP publico, regiao.
- **Arquivo:** `13-azure-vm-overview.png`
- **Legenda:** "Figura 13 — Virtual Machine em execucao na Azure."
- **Capitulo:** 7 / 10.

### 14. Azure — SKU e configuracoes

- **Tela:** portal Azure, aba "Size" da VM.
- **O que deve aparecer:** `Standard_B2ats_v2`, 2 vCPU, 1 GiB RAM.
- **Arquivo:** `14-azure-vm-sku.png`
- **Legenda:** "Figura 14 — SKU Standard_B2ats_v2 selecionada para a VM."
- **Capitulo:** 7.

### 15. Azure — Disco gerenciado

- **Tela:** portal Azure, aba "Disks" da VM.
- **O que deve aparecer:** nome e tamanho do disco do SO (Managed Disk).
- **Arquivo:** `15-azure-managed-disk.png`
- **Legenda:** "Figura 15 — Managed Disk da Virtual Machine."
- **Capitulo:** 7.

### 16. Azure — Rede e NSG

- **Tela:** portal Azure, aba "Networking" da VM.
- **O que deve aparecer:** regras do NSG (22 restrita ao seu IP, 80 liberada).
- **O que nao deve aparecer:** seu IP pessoal completo, se preferir privacidade (pode borrar parcialmente).
- **Arquivo:** `16-azure-nsg.png`
- **Legenda:** "Figura 16 — Regras de seguranca de rede (NSG)."
- **Capitulo:** 7.

### 17. Terminal SSH conectado a VM

- **Tela:** terminal local, apos `ssh azureuser@<IP>`.
- **O que deve aparecer:** prompt do Ubuntu na VM (ex.: `azureuser@GS-Cloud-API-VM:~$`).
- **O que nao deve aparecer:** o IP publico completo, se quiser manter privado (opcional).
- **Arquivo:** `17-ssh-conectado.png`
- **Legenda:** "Figura 17 — Conexao SSH estabelecida com a VM."
- **Capitulo:** 8.

### 18. Servico systemd ativo

- **Tela:** terminal SSH, apos `sudo systemctl status api-tarefas`.
- **O que deve aparecer:** "Active: active (running)".
- **Arquivo:** `18-systemd-ativo.png`
- **Legenda:** "Figura 18 — Servico systemd da API em execucao."
- **Capitulo:** 8 / 9.

### 19. Nginx funcionando

- **Tela:** terminal SSH, apos `sudo systemctl status nginx` e/ou `curl -I http://127.0.0.1`.
- **O que deve aparecer:** Nginx "active (running)" e cabecalho HTTP de resposta.
- **Arquivo:** `19-nginx-ativo.png`
- **Legenda:** "Figura 19 — Nginx ativo como proxy reverso."
- **Capitulo:** 8.

### 20. API publica acessivel

- **Tela:** navegador (ou celular em outra rede), acessando `http://<IP-PUBLICO>/docs` ou `/health`.
- **O que deve aparecer:** resposta da API pelo IP publico, fora da rede local.
- **Arquivo:** `20-api-publica.png`
- **Legenda:** "Figura 20 — API acessivel publicamente pela internet."
- **Capitulo:** 9 (Teste G).

### 21. Persistencia do SQLite apos reinicializacao

- **Tela:** terminal SSH, antes e depois de `sudo reboot`, mostrando a mesma tarefa na listagem (`curl http://127.0.0.1:8000/tarefas`).
- **O que deve aparecer:** a mesma tarefa de controle presente nas duas capturas.
- **Arquivo:** `21-persistencia-reboot.png`
- **Legenda:** "Figura 21 — Persistencia de dados confirmada apos reinicializacao da VM."
- **Capitulo:** 9 (Teste I).

---

## Checklist rapido

- [ ] 01 — Estrutura de pastas (VS Code)
- [ ] 02 — main.py
- [ ] 03 — models.py
- [ ] 04 — Swagger geral
- [ ] 05 — POST (201)
- [ ] 06 — GET (200)
- [ ] 07 — PUT (200)
- [ ] 08 — DELETE (204)
- [ ] 09 — SQLite com registros
- [ ] 10 — Pytest aprovado
- [ ] 11 — GitHub
- [ ] 12 — Azure Resource Group
- [ ] 13 — Azure VM overview
- [ ] 14 — Azure SKU
- [ ] 15 — Azure Managed Disk
- [ ] 16 — Azure NSG
- [ ] 17 — SSH conectado
- [ ] 18 — systemd ativo
- [ ] 19 — Nginx ativo
- [ ] 20 — API publica acessivel
- [ ] 21 — Persistencia apos reboot
