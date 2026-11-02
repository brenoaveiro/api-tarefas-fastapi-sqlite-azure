# Diagrama 3 — Modelo Entidade-Relacionamento

O projeto possui uma unica tabela, `tarefas`, sem relacionamentos com
outras tabelas (escopo academico pequeno e intencional).

```mermaid
erDiagram
    TAREFAS {
        INTEGER id PK "autoincrement"
        VARCHAR_200 titulo "NOT NULL"
        VARCHAR_2000 descricao "NULL permitido"
        BOOLEAN concluida "NOT NULL, default FALSE"
        DATETIME criada_em "NOT NULL, UTC"
        DATETIME atualizada_em "NOT NULL, UTC"
    }
```

**Restricoes e tipos:**

| Campo | Tipo SQL | Restricoes |
|---|---|---|
| id | INTEGER | Chave primaria, gerado automaticamente |
| titulo | VARCHAR(200) | Obrigatorio, 1 a 200 caracteres |
| descricao | VARCHAR(2000) | Opcional |
| concluida | BOOLEAN | Obrigatorio, padrao `false` |
| criada_em | DATETIME (UTC) | Obrigatorio, preenchido na criacao |
| atualizada_em | DATETIME (UTC) | Obrigatorio, atualizado em cada PUT |
