# Guia de Infraestrutura e Deploy na Microsoft Azure

Este guia descreve a arquitetura planejada, os custos estimados (com
fonte), os passos de provisionamento manual (feitos por voce, no
portal Azure, pois exigem sua conta e autorizacao de custos) e os
passos automatizados pelos scripts em `deploy/`.

> **Este guia e generico e planejado.** Os valores efetivamente implantados
> (regiao, SKU `Standard_B2ats_v2`, nomes `GS_Cloud_API...`, custos e testes) estao em
> [`DEPLOY_AZURE_REAL.md`](DEPLOY_AZURE_REAL.md). A `Standard_B1s` citada abaixo nao esta
> disponivel na assinatura Azure for Students usada no projeto.

---

## 1. Recursos da arquitetura

| Recurso | Papel |
|---|---|
| Azure Subscription | Conta de cobranca onde os recursos sao criados |
| Resource Group | Agrupa todos os recursos deste projeto para facilitar gestao e exclusao |
| Virtual Network (VNet) + Subnet | Rede isolada onde a VM recebe seu IP interno |
| Network Security Group (NSG) | Firewall de rede: libera/bloqueia portas (22, 80, 443) |
| Public IP Address | Endereco IP publico para acesso externo |
| Network Interface (NIC) | Conecta a VM a subnet e ao IP publico |
| Virtual Machine | Maquina Ubuntu Server LTS onde a aplicacao roda |
| Managed Disk (OS Disk) | Disco persistente da VM, onde o SQLite e armazenado |

---

## 2. SKU da VM: `Standard_B1s`

Dados confirmados na documentacao e nas tabelas de precos oficiais da
Azure (consultadas em novembro de 2026):

| Caracteristica | Valor |
|---|---|
| vCPU | 1 |
| Memoria RAM | 1 GiB |
| Disco temporario (local) | 4 GiB (NAO usar para o SQLite) |
| Tipo | Burstable (acumula "creditos de CPU" para picos) |
| Max. discos de dados | 2 |
| Max. interfaces de rede | 2 |

Fonte: [Bv1 size series — Microsoft Learn](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/general-purpose/bv1-series)

### Custo estimado (compute, pay-as-you-go, regiao East US)

| Item | Custo aproximado |
|---|---|
| VM `Standard_B1s` (Linux, pay-as-you-go) | ~US$ 0,0104/hora ≈ **US$ 7,59/mes** (730h) |
| Managed Disk (Standard SSD, 30 GiB, exemplo) | ~US$ 0,46/mes (US$ 0,01533/GiB/mes) |
| Public IP (SKU Standard, unico modelo disponivel desde 09/2025) | ~US$ 0,005/hora ≈ **US$ 3,65/mes** |
| Trafego de saida (egress) | Primeiros 100 GB/mes gratuitos na maioria das regioes; acima disso, cobranca por GB |

**Estimativa total aproximada: US$ 11 a US$ 13/mes**, variando por
regiao, tipo de disco e volume de trafego. **Confirme os valores atuais
na [Calculadora de Precos da Azure](https://azure.microsoft.com/pricing/calculator/) antes de provisionar.**

### Beneficio gratuito (conta Azure gratuita, se aplicavel)

Uma conta Azure Free (nova) inclui **750 horas/mes de VM B1s por 12
meses** — ou seja, uma unica VM B1s rodando o mes inteiro pode ficar
dentro da cota gratuita de compute. **Isso cobre apenas a VM**; o
Public IP Standard e o Managed Disk **nao sao cobertos integralmente**
pelo nivel gratuito e podem gerar cobranca mesmo em conta gratuita.
Verifique sua elegibilidade e os limites atuais em
[Criar conta gratuita da Azure](https://azure.microsoft.com/pricing/purchase-options/azure-account/) antes de assumir custo zero.

Fontes:
[Holori — B1s pricing](https://calculator.holori.com/azure/vm/standard-b1s),
[Azure Public IP pricing](https://azure.microsoft.com/pricing/details/ip-addresses/),
[Azure Managed Disks pricing](https://azure.microsoft.com/pricing/details/managed-disks/).

### Disponibilidade da SKU

A `Standard_B1s` esta amplamente disponivel nas regioes principais
(East US, West Europe, Brazil South, etc.), mas a disponibilidade por
regiao pode variar. **Verifique no portal Azure, ao escolher a regiao,
se `Standard_B1s` aparece na lista de tamanhos disponiveis** antes de
criar a VM. Se nao estiver disponivel na sua regiao preferida, a
alternativa de menor custo recomendada e `Standard_B1ms` (1 vCPU, 2 GiB
RAM) — nao migre automaticamente para uma SKU maior sem necessidade.

---

## 3. Seguranca de rede planejada (NSG)

| Porta | Protocolo | Origem permitida | Finalidade |
|---|---|---|---|
| 22 | TCP | **Apenas o IP publico do administrador** (voce) | Acesso SSH |
| 80 | TCP | Qualquer origem (`*`) | HTTP publico (Nginx) |
| 443 | TCP | Qualquer origem (`*`), somente se houver certificado configurado | HTTPS publico (Nginx) |
| 8000 | — | **Nenhuma** (nao criar regra) | Uvicorn — acesso apenas via `127.0.0.1`, nunca pela internet |

**Nunca libere a porta 22 para `Qualquer origem (0.0.0.0/0)`.** Restrinja
ao seu IP atual (descubra em https://www.whatismyip.com) e atualize a
regra caso seu IP mude.

---

## 4. HTTPS — o que e realmente possivel sem dominio proprio

- **Sem um dominio registrado e apontado para o IP publico da VM, NAO e
  possivel obter um certificado TLS valido** (autoridades certificadoras
  como Let's Encrypt exigem um nome de dominio, nunca emitem certificado
  para IP puro).
- Nessa situacao, a aplicacao so pode ser demonstrada via **HTTP** no IP
  publico (`http://<IP>/incidentes`), o que e aceitavel para fins
  academicos, mas deve ser destacado como limitacao no relatorio.
- **Se e somente se** voce possuir um dominio (ex.: comprado ou um
  subdominio gratuito como DuckDNS/No-IP apontado para o IP da VM),
  posso configurar HTTPS real com Certbot. Nesse caso, me informe o
  dominio exato — nao vou inventar nem presumir um.

---

## 5. O que voce precisa fazer no Portal Azure (passo a passo)

Estas etapas exigem sua conta e sua autorizacao de custo — nao podem
ser automatizadas por este assistente.

1. Acesse https://portal.azure.com e entre com sua conta Microsoft.
2. Confirme a assinatura ativa (Free Trial ou Pay-As-You-Go) em
   **"Subscriptions"**.
3. Crie um **Resource Group**: "Create a resource" → "Resource group" →
   nome sugerido `GS_Cloud_API` → regiao sugerida `East US` (ou
   `Brazil South`, se preferir menor latencia) → **Review + create**.
4. Crie a **Virtual Machine**:
   - "Create a resource" → "Virtual Machine".
   - Resource group: `GS_Cloud_API`.
   - Nome da VM: `GS-Cloud-API-VM`.
   - Regiao: a mesma do Resource Group.
   - Imagem: **Ubuntu Server 24.04 LTS** (ou a LTS mais recente disponivel).
   - Tamanho (Size): **Standard_B1s** (clique em "See all sizes" se nao
     aparecer na lista inicial).
   - Autenticacao: **SSH public key** (gere um par de chaves local ou
     use uma chave existente — nunca compartilhe a chave privada).
   - Portas de entrada: selecione apenas **"Allow selected ports"** →
     marque somente **SSH (22)** nesta etapa (80/443 serao ajustados no
     NSG depois, restringindo a origem).
   - Disco do SO: **Standard SSD** (suficiente e mais barato que Premium
     SSD para este projeto).
   - Revise o resumo de custo estimado exibido pelo proprio portal antes
     de clicar em **"Create"**.
5. Apos a criacao, anote o **IP publico** exibido na pagina de visao
   geral da VM.
6. Ajuste o **NSG** da VM (aba "Networking"):
   - Edite a regra da porta 22 para restringir a origem ao seu IP
     atual (CIDR `<seu-ip>/32`), em vez de "Any".
   - Adicione uma regra permitindo a porta 80 (`Any` origem, destino
     `Any`, protocolo TCP).
7. Conecte via SSH (no seu terminal local):
   ```bash
   ssh -i /caminho/para/sua-chave.pem azureuser@<IP-PUBLICO-DA-VM>
   ```
8. Na VM, execute o script de instalacao (ver secao 6).
9. Configure um **alerta de orcamento** (recomendado): "Cost
   Management + Billing" → "Budgets" → "Add" → defina um valor mensal
   (ex.: US$ 15) e um e-mail de alerta. **Um alerta de orcamento NAO
   bloqueia gastos automaticamente** — ele apenas notifica.
10. Ao final do trabalho academico, **exclua o Resource Group**
    (`GS_Cloud_API`) para parar toda cobranca: "Resource groups" →
    selecione `GS_Cloud_API` → "Delete resource group".

---

## 6. Instalacao automatizada (depois de ter SSH na VM)

Depois de conectado via SSH na VM, com o repositorio publicado no
GitHub:

```bash
# Dentro da VM, com um usuario com sudo (ex.: azureuser):
sudo apt-get update -y && sudo apt-get install -y git
git clone https://github.com/<seu-usuario>/api-tarefas-fastapi-sqlite-azure.git /tmp/api-tarefas-instalador
cd /tmp/api-tarefas-instalador
chmod +x deploy/install.sh
sudo ./deploy/install.sh https://github.com/<seu-usuario>/api-tarefas-fastapi-sqlite-azure.git
```

O script `deploy/install.sh`:
1. Atualiza os pacotes do sistema.
2. Instala Python, Nginx, Git e sqlite3.
3. Cria o usuario de servico `apitarefas` (sem privilegios).
4. Cria `/opt/api-tarefas` (codigo) e `/var/lib/api-tarefas` (dados
   persistentes).
5. Clona o repositorio.
6. Cria o ambiente virtual Python e instala as dependencias.
7. Configura o `.env` (sem sobrescrever um existente).
8. Inicializa o banco de dados.
9. Instala e inicia o servico systemd `api-tarefas`.
10. Configura e recarrega o Nginx.
11. Executa um health check local automatico ao final.

---

## 7. Operacao do servico (systemd)

| Acao | Comando |
|---|---|
| Iniciar | `sudo systemctl start api-tarefas` |
| Parar | `sudo systemctl stop api-tarefas` |
| Reiniciar | `sudo systemctl restart api-tarefas` |
| Status | `sudo systemctl status api-tarefas` |
| Logs em tempo real | `sudo journalctl -u api-tarefas -f` |
| Logs das ultimas 100 linhas | `sudo journalctl -u api-tarefas -n 100 --no-pager` |
| Habilitar na inicializacao | `sudo systemctl enable api-tarefas` (ja feito pelo install.sh) |

### Diagnosticando uma falha

1. `sudo systemctl status api-tarefas` — veja se o servico esta
   "active (running)" ou "failed".
2. `sudo journalctl -u api-tarefas -n 100 --no-pager` — leia o erro mais
   recente.
3. `curl http://127.0.0.1:8000/health` (direto na VM) — testa se o
   Uvicorn responde, isolando se o problema e na aplicacao ou no Nginx.
4. `sudo nginx -t` — valida a sintaxe da configuracao do Nginx.
5. `sudo systemctl status nginx` — verifica se o Nginx esta ativo.

### Atualizando o codigo

```bash
sudo /opt/api-tarefas/deploy/deploy.sh
```

### Reiniciando a VM (teste de resiliencia)

```bash
sudo reboot
```

Como o servico foi habilitado com `systemctl enable`, ele deve iniciar
automaticamente apos o boot. Aguarde ~1 minuto e valide:

```bash
curl http://127.0.0.1:8000/health
sudo systemctl status api-tarefas
```

### Backup e restauracao do SQLite

```bash
# Backup (seguro mesmo com a aplicacao rodando):
sudo /opt/api-tarefas/deploy/backup.sh

# Restauracao (ver instrucoes completas impressas pelo proprio backup.sh):
sudo systemctl stop api-tarefas
sudo cp /var/lib/api-tarefas/backups/tarefas_<timestamp>.db /var/lib/api-tarefas/tarefas.db
sudo chown apitarefas:apitarefas /var/lib/api-tarefas/tarefas.db
sudo systemctl start api-tarefas
```

---

## 8. Controle de custos — checklist antes de criar recursos pagos

- [ ] Confirmei a regiao e a disponibilidade da SKU `Standard_B1s` no portal.
- [ ] Consultei a Calculadora de Precos da Azure com a regiao e o disco escolhidos.
- [ ] Sei que o Public IP Standard gera custo mesmo com a VM parada.
- [ ] Configurei um alerta de orcamento em "Cost Management + Billing".
- [ ] Entendo que o alerta nao bloqueia gastos — apenas notifica.
- [ ] Defini a data em que vou excluir o Resource Group ao final do trabalho.

---

## 9. Diferenca entre SQLite, disco gerenciado e armazenamento Azure

- **Managed Disk (disco gerenciado da VM)**: disco virtual persistente
  anexado à VM, onde o sistema operacional e os arquivos da aplicacao
  (incluindo o `.db` do SQLite) ficam armazenados. Sobrevive a reinicios
  da VM.
- **Disco temporario (`/mnt` ou `/dev/sdb` na B1s, 4 GiB)**: usado pelo
  sistema para swap/cache; **pode ser perdido** em determinadas
  operacoes de manutencao/realocacao da VM. **O SQLite nunca deve ficar
  aqui.**
- **Azure Blob Storage / Azure SQL Database**: servicos gerenciados
  separados, cobrados e configurados independentemente da VM — **nao
  utilizados neste projeto**. Nao confundir com o Managed Disk da VM.
