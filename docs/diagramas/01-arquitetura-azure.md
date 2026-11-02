# Diagrama 1 — Arquitetura Azure

Representa a fronteira entre os recursos Azure (nuvem) e os componentes
internos da VM (sistema operacional). O NSG atua como controle de
trafego de rede (firewall), nunca como servidor de aplicacao.

```mermaid
flowchart TB
    Usuario["Usuario / Navegador / Cliente HTTP"]

    subgraph Internet[" Internet "]
        Usuario
    end

    subgraph Azure["Microsoft Azure — Resource Group"]
        PublicIP["Public IP Address"]
        NSG["Network Security Group\n(controle de trafego: 22, 80, 443)"]
        VNet["Virtual Network / Subnet"]

        subgraph VM["Azure Virtual Machine — Ubuntu Server LTS (Standard_B1s)"]
            Nginx["Nginx\n(proxy reverso — portas 80/443)"]
            Uvicorn["Uvicorn + FastAPI\n(127.0.0.1:8000 — nao exposto)"]
            SQLite["SQLite\n/var/lib/api-tarefas/tarefas.db\n(Managed Disk)"]

            Nginx -->|proxy_pass| Uvicorn
            Uvicorn -->|leitura/escrita| SQLite
        end

        PublicIP --- NSG
        NSG --- VNet
        VNet --- VM
    end

    Usuario -->|HTTP/HTTPS| PublicIP

    classDef azureBox fill:#e6f2ff,stroke:#0066cc;
    classDef vmBox fill:#fff7e6,stroke:#cc8400;
    class Azure azureBox
    class VM vmBox
```

**Observacoes:**
- O NSG controla quais portas podem receber trafego da internet (22 restrita ao IP do administrador; 80/443 liberadas; 8000 nunca exposta publicamente).
- O Managed Disk armazena o arquivo SQLite de forma persistente — ele nao e perdido ao reiniciar a VM, diferente do disco temporario local.
- O Uvicorn escuta somente em `127.0.0.1`, portanto so pode ser acessado pelo Nginx na mesma maquina.
