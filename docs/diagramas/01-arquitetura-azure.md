# Diagrama 1 — Arquitetura Azure da CyberIncident API

```mermaid
flowchart TB
    Usuario["Navegador / Cliente HTTP"]

    subgraph Azure["Microsoft Azure — Resource Group GS_Cloud_API (North Central US)"]
        PIP["IP publico GS_Cloud_API_IP\nStandard, estatico"]
        NSG["NSG GS_Cloud_API_NSG\n22: so IP do administrador | 80 e 443: publicas"]
        VN["Rede virtual GS_Cloud_API_VNet 10.10.0.0/16
Sub-rede GS_Cloud_API_Subnet 10.10.1.0/24"]
        subgraph VM["VM GS-Cloud-API-VM — Ubuntu 24.04 — Standard_B2ats_v2 (2 vCPU, 1 GiB)"]
            Nginx["Nginx :80 e :443 (TLS Let's Encrypt)
proxy reverso + bloqueio de escrita por IP"]
            App["Uvicorn + FastAPI
127.0.0.1:8000 (nao exposto)"]
            DB[("SQLite
/var/lib/api-tarefas/tarefas.db
tabela incidentes")]
        end
        Disco["Managed Disk GS_Cloud_API_Disk\nStandard SSD LRS, 32 GiB"]
    end

    Usuario -->|HTTPS 443 ou HTTP 80| PIP --> NSG --> VN --> Nginx
    Nginx -->|proxy_pass| App
    App -->|SQLAlchemy| DB
    DB -.->|armazenado em| Disco
```

- O **NSG** funciona como firewall: SSH somente do IP do administrador, HTTP (80) e HTTPS (443) publicos; a porta 8000 nunca e liberada.
- O **Nginx** libera leitura (GET) para todos e restringe POST/PUT/PATCH/DELETE a IPs autorizados.
- O arquivo SQLite fica no **Managed Disk**, que persiste mesmo se a VM for reiniciada.
- O HTTPS usa certificado Let's Encrypt emitido para o IP (curta duracao, renovacao automatica por timer do systemd).
