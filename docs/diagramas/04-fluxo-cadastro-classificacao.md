# Diagrama 4 — Cadastro e classificacao de incidentes

```mermaid
flowchart LR
    A["POST /incidentes\ntitulo, descricao, categoria,\nseveridade, ip_origem..."] --> B{"Dados validos?\nenums, IP, tamanhos"}
    B -->|nao| E["422 Dados invalidos"]
    B -->|sim| C["Grava no SQLite\nstatus = aberto"]
    C --> D["201 Created"]
    D --> F["Classificacao e tratamento"]

    subgraph Fluxo["Status do incidente (PATCH /incidentes/id/status)"]
        direction LR
        S1(["aberto"]) --> S2(["em_analise"])
        S2 --> S3(["contido"])
        S3 --> S2
        S2 --> S4(["resolvido"])
        S3 --> S4
        S4 -->|reabertura| S1
    end
    F --> Fluxo
```

- Severidade: `baixa`, `media`, `alta`, `critica`. Categoria: phishing, malware, acesso_indevido, forca_bruta, vazamento_dados, anomalia_rede, outros.
- Ao **resolver**, `resolvido_em` recebe a data/hora UTC; ao **reabrir**, o campo e limpo.
- Transicoes fora do fluxo (ex.: `aberto` direto para `resolvido`) retornam HTTP 422.
