# Diagrama 5 — Fluxo de deploy: GitHub para Azure

```mermaid
flowchart LR
    A["Desenvolvimento local\nPython + pytest"] -->|git commit / push| B["GitHub\nrepositorio"]
    B -->|git pull na VM| C["VM GS-Cloud-API-VM\n/opt/api-tarefas"]
    C --> D["deploy.sh\n1. backup SQLite\n2. git pull\n3. pip install\n4. unidade systemd\n5. restart"]
    D -->|falha no backup| X["Deploy abortado\nnenhuma alteracao"]
    D --> E["Servico api-tarefas\nsystemd + Uvicorn"]
    E --> F["Nginx :80"]
    F --> G["Validacao: /health,\ndashboard, Swagger, CRUD"]
```

- O banco **nao** e recriado: a migracao cria apenas a tabela `incidentes`, se ela nao existir.
- O `.env`, o arquivo do SQLite e a configuracao do Nginx da VM nao vao para o GitHub.
