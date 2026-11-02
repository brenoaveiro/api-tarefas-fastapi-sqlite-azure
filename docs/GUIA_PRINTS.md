# Guia de Evidências (prints) — CyberIncident API

As 18 evidências do trabalho ficam na pasta `Print_GS` (Área de Trabalho), organizadas assim:

| Pasta | Figuras |
|---|---|
| `01_Infraestrutura_Azure` | 01 Resource Group · 02 Máquina virtual · 03 SKU, vCPU e RAM · 04 Armazenamento · 05 Rede · 06 NSG |
| `02_CyberIncident_Dashboard` | 07 Dashboard |
| `03_Swagger_API` | 08 Swagger personalizado · 09 Health Check · 10 POST /incidentes · 11 GET /incidentes/{id} · 12 PATCH status · 13 Estatísticas |
| `04_SQLite_VM` | 14 Serviço systemd · 15 SQLite (tabela `incidentes`) · 16 Persistência após reinício |
| `05_GitHub_Testes` | 17 GitHub · 18 Pytest |
| `06_Diagramas` | 6 diagramas em PNG |
| `07_Relatorio` | `relatorio-final.docx` e `relatorio-final.pdf` |

O arquivo `RELATORIO_EVIDENCIAS.md` lista, para cada figura, o que ela comprova, a legenda e como foi obtida. Os prints da versão anterior (API de tarefas) foram preservados em `Print_GS_backup_tarefas` e **não** devem ser usados como evidência da versão atual.

## Como cada figura foi obtida

- **01 a 06 (Portal Azure):** capturas reais do Portal. Script `Print_GS/capturar_portal_azure.py`: abre o Chrome, aguarda o login do próprio aluno (não contorna MFA) e navega pelo menu lateral até cada tela, validando o conteúdo antes de salvar. O ID da assinatura e o IP do administrador são mascarados.
- **07 a 13 e 17:** páginas reais abertas no Chrome (Playwright). As requisições das Figuras 09 a 13 usam o botão *Try it out* do Swagger. A faixa escura superior (URL e horário) é acrescentada na captura.
- **14, 15, 16 e 18:** janelas reais de console (PowerShell) executando os comandos de verdade (SSH, curl e pytest); a janela é capturada. O IP do administrador aparece mascarado (`45.190.xxx.xxx`).

## Refazer uma captura

```bash
python capturar_portal_azure.py              # Figuras 01-06 (Portal; pede login)
python capturar_portal_azure.py Figura_03    # somente uma figura
```

Ao tirar prints manualmente no Portal, cubra o IP do administrador (regra `allow-ssh-admin` do NSG) e o ID da assinatura.
