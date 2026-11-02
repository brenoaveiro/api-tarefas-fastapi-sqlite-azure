# Roteiro de Apresentação (5 a 10 minutos)

Abas abertas antes de começar: dashboard (`https://20.80.10.214/`), Swagger (`/docs`), GitHub, Portal Azure (Resource Group `GS_Cloud_API`) e um terminal. **A escrita (POST/PATCH) só funciona do IP autorizado**: apresente do computador usado nos testes ou peça a liberação de outro IP antes.

## 1. Introdução (45 s)
Um SOC recebe alertas o tempo todo e precisa registrar cada incidente, classificá-lo por severidade e acompanhá-lo até a resolução. A CyberIncident API simula esse registro com **dados fictícios**: ela não detecta ameaças, demonstra uma API REST em nuvem.

## 2. Arquitetura (1 min)
Mostre o Diagrama 1: navegador → IP público → NSG → rede virtual → **Nginx** (portas 443 e 80) → **Uvicorn/FastAPI** (`127.0.0.1:8000`, não exposto) → **SQLite** no disco gerenciado. O Nginx é a única porta de entrada; isso reduz a superfície de ataque.

## 3. Tecnologias e SQLite (1 min)
Python e FastAPI (rotas e validação), Pydantic (regras dos dados), SQLAlchemy (ORM) e SQLite, que guarda tudo em um arquivo, sem servidor de banco e sem custo extra. Limite: não é indicado para muita escrita simultânea.

## 4. Azure: VM, SKU e armazenamento (1,5 min)
No Portal, mostre o Resource Group e a VM `GS-Cloud-API-VM`: **Standard_B2ats_v2** (2 vCPU, 1 GiB de RAM, Ubuntu 24.04), disco **Standard SSD de 32 GiB** (persistente), VNet, IP público e NSG (SSH só do administrador, HTTP na 80, HTTPS na 443). Pergunta provável: *por que não a B1s?* A B1s não está liberada na assinatura Azure for Students; esta foi a menor opção permitida com cota.

## 5. Dashboard (1 min)
Abra `/`: cartões (total, críticos, abertos, resolvidos), gráfico por severidade e tabela dos mais recentes. **Todos os números vêm do SQLite**, sem dados inventados.

## 6. Swagger personalizado (30 s)
Abra `/docs`: tema próprio, seções Sistema, Incidentes e Estatísticas, e execução real das requisições.

## 7. Cadastro (1 min)
`POST /incidentes` com um incidente fictício: resposta **201** com o `id`; status inicial `aberto`. Mostre que dados inválidos (severidade inexistente, IP errado) dão **422**.

## 8. Consulta e classificação (1 min)
`GET /incidentes?severidade=critica` e `GET /incidentes/{id}`. Depois `PATCH /incidentes/{id}/status` para `em_analise`; tente pular direto para `resolvido` e mostre o **422** (fluxo de tratamento).

## 9. Estatísticas (30 s)
`GET /incidentes/estatisticas`: contagens por status, severidade e categoria, coerentes com o dashboard.

## 10. Persistência (45 s)
Mostre o SQLite no servidor e o serviço reiniciado (`systemctl restart api-tarefas`): o incidente continua lá, pois o arquivo está no disco gerenciado.

## 11. GitHub e testes (45 s)
Repositório com código, `deploy/`, `docs/` e `tests/`. Rode `python -m pytest -q`: **96 testes aprovados**, sem avisos. Na VM, 58 verificações públicas aprovadas, e o CI do GitHub passa.

## 12. Conclusão (30 s)
API publicada, testada e documentada; infraestrutura Azure preservada e reaproveitada. Limitações honestas: sem autenticação de usuários (a escrita é restrita por IP), certificado de curta duração, SQLite para baixa concorrência e VM única. Melhorias: token de API, domínio com certificado de 90 dias e banco gerenciado.

## Perguntas prováveis

| Pergunta | Resposta curta |
|---|---|
| O que é um NSG? | Firewall do Azure que decide quais portas e origens podem acessar a VM. |
| Por que Nginx na frente do FastAPI? | Recebe o tráfego, aplica o bloqueio de escrita por IP e deixa o Uvicorn escondido em `127.0.0.1`. |
| O que é um Managed Disk? | Disco virtual persistente do Azure; o SQLite fica nele e sobrevive a reinícios. |
| A API tem login? | Não. A escrita é protegida por IP no Nginx; autenticação seria a próxima melhoria. |
| Como funciona o HTTPS sem domínio? | O Let's Encrypt passou a emitir certificados para endereços IP (validade de cerca de 6 dias); o Certbot renova sozinho duas vezes ao dia e o Nginx recarrega o certificado. O HTTP segue ativo como contingência. |
| Quanto custa? | Cerca de US$ 13 por mês ligada 24 h (VM, disco e IP); desalocar a VM zera a computação. |
| O que aconteceu com a API de tarefas? | O projeto evoluiu: a infraestrutura e o banco foram reaproveitados e a tabela antiga foi preservada. |
