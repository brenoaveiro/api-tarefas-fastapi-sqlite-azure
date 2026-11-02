# Diagrama 6 — Fluxo de testes e validacao

```mermaid
flowchart LR
    A["pytest local\n55 testes"] --> B["Banco SQLite\ntemporario isolado"]
    B --> C{"Todos passam?"}
    C -->|nao| D["Corrigir e repetir"]
    C -->|sim| E["Commit e push\nGitHub"]
    E --> F["Deploy na VM Azure"]
    F --> G["testar_producao.sh\n30 verificacoes na URL publica"]
    G --> H["CRUD, estatisticas,\npersistencia apos reinicio,\nporta 8000 fechada,\nescrita bloqueada (403)"]
```

- Testes locais: API, validacoes, migracao, persistencia, interface, seguranca (XSS, SQL injection, CORS) e configuracao do Nginx e do systemd.
- Testes em producao: executados contra o IP publico, com limpeza dos dados de teste.
