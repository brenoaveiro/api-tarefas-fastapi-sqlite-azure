# Implantacao real na Azure — dados verificados

Documento gerado a partir da execucao real do deploy em **2026-11-02**.
Todos os valores abaixo foram lidos da propria Azure ou da VM; os testes
estao em `docs/evidencias/testes-producao.txt`.

> **Nomes de identificacao da prova (Global Solution / Cloud / API):** o
> ambiente foi recriado com o padrao `GS_Cloud_API`, pois a Azure nao permite
> renomear Resource Group nem VM. O nome da VM usa hifens
> (`GS-Cloud-API-VM`) porque a Azure nao aceita underscore em nome de VM.

## 1. Por que nao foi usada a `Standard_B1s`

A assinatura **Azure for Students** (tenant "Grupo Alun") tem uma politica
("Allowed resource deployment regions") que so permite criar recursos em:
`southafricanorth`, `northcentralus`, `brazilsouth`, `eastus2`, `mexicocentral`.
Alem disso:

- `Standard_B1s` (e B1ls, B2s) **nao estao disponiveis** para a assinatura em
  `eastus` e `brazilsouth`;
- as VMs sem restricao em `brazilsouth`/`eastus` (serie F1 v7, D2 v7) tem
  **cota 0**; `eastus2` e `mexicocentral` nao tinham VM pequena com cota;
- `canadaeast` tinha VMs liberadas, mas a politica **bloqueia** a regiao;
- `northcentralus` (Iowa, EUA) tinha a serie B v2 liberada, com cota.

Escolha final: **`Standard_B2ats_v2`** em **`northcentralus`**, a opcao mais
barata permitida.

Antes de qualquer consulta foi preciso registrar (gratuito) os provedores
`Microsoft.Compute`, `Microsoft.Network` e `Microsoft.Storage`, que estavam
*NotRegistered*.

## 2. Recursos criados

| Item | Valor |
|---|---|
| Regiao | `northcentralus` (North Central US) |
| Resource Group | `GS_Cloud_API` |
| Virtual Machine | `GS-Cloud-API-VM` |
| SKU | `Standard_B2ats_v2` (burstable, AMD) |
| vCPU / RAM | 2 vCPU / 1 GiB (~0,9 GiB uteis) + swap de 1 GiB criado por nos |
| Sistema operacional | Ubuntu Server 24.04.5 LTS (x86_64) |
| Disco do SO | Managed Disk `GS_Cloud_API_Disk`, Standard SSD LRS, 32 GiB (~30 GiB uteis) |
| Rede virtual | `GS_Cloud_API_VNet` 10.10.0.0/16, sub-rede `GS_Cloud_API_Subnet` 10.10.1.0/24 |
| IP privado | 10.10.1.4 |
| IP publico | `GS_Cloud_API_IP`, SKU Standard, estatico, IPv4: **20.80.10.214** |
| NSG | `GS_Cloud_API_NSG` |
| Autenticacao | SSH por chave publica (usuario `azureuser`, sem senha) |

### Regras do NSG

| Prioridade | Nome | Porta | Origem | Acao |
|---|---|---|---|---|
| 100 | allow-ssh-admin | 22/TCP | IP do administrador (/32) | Permitir |
| 110 | allow-http | 80/TCP | Qualquer | Permitir |
| padrao | DenyAllInBound | todas | Qualquer | Negar |

A porta 8000 (Uvicorn) **nao** e exposta: o Uvicorn escuta so em 127.0.0.1 e
o NSG nao a libera. Teste: `curl http://20.80.10.214:8000/health` -> sem resposta.

## 3. Software na VM

Python 3 + FastAPI + Uvicorn (venv em `/opt/api-tarefas/.venv`), Nginx como
proxy reverso na porta 80, systemd (`api-tarefas.service`, usuario sem
privilegios `apitarefas`), SQLite em `/var/lib/api-tarefas/tarefas.db`
(modo WAL, permissao 600, dono `apitarefas`) no Managed Disk persistente.

## 4. Comandos usados (resumo)

```bash
az provider register -n Microsoft.Compute --wait      # idem Network, Storage
az group create -n GS_Cloud_API -l northcentralus
az network vnet create -g GS_Cloud_API -n GS_Cloud_API_VNet --address-prefix 10.10.0.0/16 \
   --subnet-name GS_Cloud_API_Subnet --subnet-prefix 10.10.1.0/24
az network nsg create -g GS_Cloud_API -n GS_Cloud_API_NSG
az network nsg rule create ... -n allow-ssh-admin --priority 100 --source-address-prefixes <SEU-IP>/32 --destination-port-ranges 22
az network nsg rule create ... -n allow-http --priority 110 --destination-port-ranges 80
az network public-ip create -g GS_Cloud_API -n GS_Cloud_API_IP --sku Standard --allocation-method Static
az vm create -g GS_Cloud_API -n GS-Cloud-API-VM --size Standard_B2ats_v2 \
   --image Canonical:ubuntu-24_04-lts:server:latest --admin-username azureuser \
   --ssh-key-values ~/.ssh/id_ed25519_apitarefas.pub --authentication-type ssh \
   --vnet-name GS_Cloud_API_VNet --subnet GS_Cloud_API_Subnet --nsg GS_Cloud_API_NSG \
   --public-ip-address GS_Cloud_API_IP --os-disk-size-gb 32 --storage-sku StandardSSD_LRS
# na VM:
sudo ./install.sh https://github.com/brenoaveiro/api-tarefas-fastapi-sqlite-azure.git
```

## 5. Protecao de escrita (API sem autenticacao)

Como a API nao tem login, o Nginx deixa **GET/HEAD/OPTIONS publicos** e exige
IP autorizado para **POST/PUT/PATCH/DELETE** (`limit_except` em
`deploy/nginx/api-tarefas.conf`). Os IPs autorizados ficam em
`/etc/nginx/api-tarefas-writers.conf` (somente na VM, fora do Git):

```
allow 127.0.0.1;
allow <SEU-IP>;
```

Sem esse arquivo ninguem escreve. Verificado: da VM (IP nao autorizado)
POST/PUT/DELETE -> **403**; do computador autorizado -> 201/200/204.
Use apenas dados ficticios.

## 6. HTTPS

**Nao ha HTTPS.** Nao existe dominio proprio apontado para o IP, e nao e
possivel emitir certificado valido (Let's Encrypt) para um IP puro. A API
esta em **HTTP**, o que **nao e uma conexao segura** (trafego sem
criptografia). Para HTTPS: registrar um dominio, apontar para o IP e rodar
`sudo certbot --nginx -d seu-dominio`.

## 7. Resultados dos testes (reais)

Executados por `scripts/testar_producao.sh` contra `http://20.80.10.214`
(CyberIncident API): **30 aprovados, 0 falhas** — health 200, dashboard e Swagger
200 (sem CDN), estatisticas coerentes com a listagem, POST 201, GET 200, PUT 200,
PATCH 200 e 422 em transicao invalida, DELETE 204, 404 em id inexistente,
persistencia apos `systemctl restart api-tarefas`, porta 8000 sem resposta,
POST/PUT/PATCH/DELETE de IP nao autorizado = 403 e tabela antiga `tarefas`
preservada. Saida completa em `docs/evidencias/testes-producao.txt`.
Testes automatizados locais: **55 aprovados** (40 da CyberIncident API + 15 do instalador).

## 8. Custos estimados (Linux, pay-as-you-go, ligada 24 h)

| Recurso | Preco de tabela | ~Mes (730 h) |
|---|---|---|
| VM B2ats_v2 (northcentralus) | US$ 0,0094/h | ~US$ 6,86 |
| Disco Standard SSD 32 GiB (E4) | ~US$ 2,64/mes (tabela canadaeast) | ~US$ 2,64 |
| IP publico Standard | ~US$ 0,005/h (tabela canadaeast) | ~US$ 3,65 |
| **Total aproximado** | | **~US$ 13/mes** |

Precos de varejo da API publica da Azure; disco e IP foram lidos de outra
regiao e podem diferir um pouco em `northcentralus`. O saldo de creditos nao
e exibido pela CLI: consulte o Portal (Assinaturas > Azure for Students >
Visao geral / Gerenciamento de Custos). **Para parar a cobranca de compute:**
`az vm deallocate -g GS_Cloud_API -n GS-Cloud-API-VM` (disco e IP continuam
cobrando). **Para parar tudo:** `az group delete -n GS_Cloud_API`.

## 9. Limitacoes

- 1 GiB de RAM (por isso o swap); suficiente para demo de baixo trafego.
- Sem autenticacao na API e sem HTTPS (ver itens 5 e 6).
- SQLite no disco do SO (Managed Disk persistente), sem disco de dados separado.
- Se o seu IP publico mudar, atualize a regra `allow-ssh-admin` do NSG e o
  arquivo `api-tarefas-writers.conf`.

## 10. Atualizacao para a CyberIncident API (2026-11-02)

A aplicacao foi transformada de uma API de tarefas em uma plataforma de
gerenciamento de incidentes de seguranca **na mesma VM**, sem recriar nenhum
recurso Azure. Passos executados:

1. Estado verificado por SSH: commit anterior `d72e3f7`, 27 GB livres, servicos ativos.
2. Backup consistente do SQLite (`sqlite3 .backup`) com `PRAGMA integrity_check = ok`.
   O backup antigo estava inoperante: `deploy/backup.sh` nao era executavel e o `deploy.sh`
   apenas avisava e seguia. Corrigido: agora usa `bash` e **aborta** se o backup falhar.
3. `git pull` e `deploy/deploy.sh` (backup, pull, pip, unidade systemd, restart, health).
4. `.env` da VM: somente `APP_NAME` e `APP_VERSION` foram ajustados (o resto foi preservado).
5. Migracao nao destrutiva: a aplicacao cria a tabela `incidentes` ao iniciar; a tabela
   `tarefas` (1 registro) permanece intacta no mesmo arquivo `tarefas.db`.
6. Dados de demonstracao: incidentes ficticios `[DEMO]`, com IPs das faixas de
   documentacao (RFC 5737), cadastrados pela API.

Rollback: voltar ao commit `d72e3f7` (`git checkout`) e reiniciar o servico; o banco
so e restaurado do backup (`/var/lib/api-tarefas/backups/`) se necessario.
