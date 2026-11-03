# Implantacao real na Azure — dados verificados

> **Status e como ler este guia.** **Durante a implantacao (2026-11-02):** a aplicacao foi publicada na VM `GS-Cloud-API-VM` (SKU `Standard_B2ats_v2`), com SQLite em Managed Disk persistente, HTTPS com certificado Let's Encrypt para o IP publico (secao 6) e 58 verificacoes de producao aprovadas (secao 7). **Situacao atual:** depois da validacao e da coleta das evidencias, o Resource Group `GS_Cloud_API` foi excluido para evitar custos; o IP `20.80.10.214` esta indisponivel e o HTTPS **nao pode ser verificado hoje**. As secoes 1 a 11 registram o que foi executado historicamente. Para uma nova implantacao seria preciso recriar os recursos Azure (nao executado), atualizar o IP nas regras do NSG, do Nginx e do certificado e emitir novo certificado. Relatorio oficial: [`GS_CloudSec_BrenoAveiro.pdf`](GS_CloudSec_BrenoAveiro.pdf).

Documento gerado a partir da execucao real do deploy em **2026-11-02**.
Todos os valores abaixo foram lidos da propria Azure ou da VM; os testes
estao em `docs/evidencias/testes-producao-20261102-180113.txt`.

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
| 120 | allow-https | 443/TCP | Qualquer | Permitir |
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

## 6. HTTPS (certificado Let's Encrypt para o IP publico)

Implementado em 2026-11-02 com `deploy/https_ip.sh`, seguindo a documentacao oficial do
Let's Encrypt (certificados de IP e de 6 dias, disponiveis em 2026) e do Certbot:

- Certbot **5.9.0** (>= 5.4) instalado em `/opt/certbot-venv`; `certonly` com `--preferred-profile shortlived`,
  `--webroot` e `--ip-address 20.80.10.214`. Os plugins `nginx`/`apache` nao instalam certificados de IP.
- Teste previo em **staging**; depois emissao real. Certificado: emissor Let's Encrypt (CN=YE1), SAN `IP:20.80.10.214`,
  validade ~6 dias (2026-11-02 19:44 a 2026-11-09 11:44 UTC na emissao inicial).
- Nginx: bloco `server` na porta 443 (`deploy/nginx/api-tarefas-https.conf`, TLS 1.2/1.3) com a **mesma politica de escrita**;
  a porta 80 ganhou apenas o desafio ACME (`/.well-known/acme-challenge/`). NSG: regra `allow-https` (443, prioridade 120).
- Renovacao: `certbot-renew.timer` (duas vezes ao dia, `Persistent=true`) e `renew_hook = systemctl reload nginx`.
  Provas: `certbot renew --dry-run` aprovado e **renovacao forcada real** (numero de serie do certificado servido mudou de
  `06A3E5...` para `06B4FC...` sem intervencao manual).
- Verificado de fora: `curl` sem `-k` (`ssl_verify_result=0`), Chrome sem erros de console, `/docs` e `/` via HTTPS,
  escrita via 443 bloqueada (403) para IP nao autorizado.
- **Sem** redirecionamento HTTP->HTTPS e **sem** HSTS (decisao deliberada): o certificado dura poucos dias e a VM pode ficar
  desalocada; o HTTP permanece como contingencia. Se a VM ficar desligada mais de 6 dias, o certificado expira e e renovado apos
  a proxima inicializacao.

Comandos: `sudo ./deploy/https_ip.sh 20.80.10.214 --staging` (teste) e `sudo ./deploy/https_ip.sh 20.80.10.214` (real).
Rollback do HTTPS: remover `/etc/nginx/sites-enabled/api-tarefas-https.conf`, `nginx -t`, `systemctl reload nginx`;
copia da configuracao anterior em `/var/lib/api-tarefas/backups/nginx_antes_https_*.tgz`.

## 7. Resultados dos testes (reais)

- Testes locais: **96 aprovados, sem avisos** (`python -m pytest -q`); CI do GitHub Actions: aprovado.
- Producao (`REQUIRE_HTTPS=1 scripts/testar_producao.sh`): **58 verificacoes, 58 aprovadas, 0 falhas, codigo de saida 0**
  (`docs/evidencias/testes-producao-20261102-180113.txt`): interface e Swagger, estatisticas coerentes, CRUD e transicoes,
  422/404, persistencia apos reiniciar o servico, porta 8000 fechada, escrita de IP nao autorizado = 403 (HTTP e HTTPS),
  permissoes do banco, certificado valido, timer e hook de renovacao, tabelas via `sqlite_master`, WAL e `integrity_check`.
- Teste negativo (SSH invalido de proposito): 13 falhas contabilizadas e codigo de saida 1.
- Auditoria de dependencias (`pip-audit`): nenhuma vulnerabilidade conhecida (o Starlette 0.41.3 anterior tinha 14).

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
cobrando). **Para parar tudo:** `az group delete -n GS_Cloud_API` (comando de encerramento aplicado ao final da validacao).

## 9. Limitacoes

- 1 GiB de RAM (por isso o swap); suficiente para demo de baixo trafego.
- Sem autenticacao individual na API: a escrita e restrita por IP no Nginx (item 5). O HTTPS foi configurado e validado em 2026-11-02 (item 6), mas sem redirecionamento HTTP->HTTPS e sem HSTS, e o certificado de curta duracao (~6 dias) depende da renovacao automatica com a VM ligada.
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

## 11. Verificacao final e rollback

- Commit implantado na VM: ver o historico de commits do repositorio. Servicos `api-tarefas`, `nginx` e `certbot-renew.timer` ativos no momento da validacao.
- Backups: `/var/lib/api-tarefas/backups/tarefas_*.db` (integridade `ok`) e `nginx_antes_https_*.tgz`; o `.env` anterior tambem foi copiado.
- Rollback de codigo: `git checkout <commit-anterior>` em `/opt/api-tarefas` e `systemctl restart api-tarefas`. O banco so e restaurado
  do backup (`cp` com o servico parado) se houver corrupcao; a tabela `tarefas` nunca e apagada.
