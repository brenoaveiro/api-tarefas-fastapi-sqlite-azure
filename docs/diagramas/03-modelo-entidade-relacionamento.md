# Diagrama 3 — Modelo de dados SQLite: tabela `incidentes`

```mermaid
erDiagram
    INCIDENTES {
        INTEGER id PK
        VARCHAR titulo
        TEXT descricao
        VARCHAR categoria "phishing, malware, acesso_indevido, forca_bruta, vazamento_dados, anomalia_rede, outros"
        VARCHAR severidade "baixa, media, alta, critica"
        VARCHAR status "aberto, em_analise, contido, resolvido"
        VARCHAR ip_origem "opcional, IPv4 ou IPv6"
        VARCHAR ativo_afetado
        VARCHAR responsavel "opcional"
        DATETIME criado_em "UTC"
        DATETIME atualizado_em "UTC"
        DATETIME resolvido_em "preenchido ao resolver"
    }
```

- Restricoes `CHECK` no banco garantem os valores validos de categoria, severidade e status.
- A tabela antiga `tarefas` (versao anterior do projeto) continua no mesmo arquivo, sem relacao com `incidentes` e sem alteracao.
