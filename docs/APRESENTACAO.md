# Roteiro de Apresentacao (5 a 10 minutos)

## Estrutura sugerida

**1. Problema (1 min)**
"Precisavamos de um sistema simples para gerenciar tarefas via API,
que pudesse ser acessado por qualquer cliente HTTP, com dados
persistidos e hospedado na nuvem."

**2. Tecnologias (1 min)**
Python 3 + FastAPI (API), Pydantic (validacao), SQLAlchemy + SQLite
(persistencia), Nginx + Uvicorn + systemd (execucao na VM), Git/GitHub
(versionamento), Pytest/HTTPX (testes).

**3. Arquitetura (1-2 min)**
Mostrar o Diagrama 1 (`docs/diagramas/01-arquitetura-azure.md`):
usuario → internet → IP publico → NSG → VM Ubuntu → Nginx → FastAPI →
SQLite.

**4. Papel da Azure (1 min)**
A VM e o unico recurso de computacao (modelo IaaS — Infrastructure as a
Service): voce controla o sistema operacional e instala tudo
manualmente, diferente de um App Service (PaaS), onde a plataforma
gerencia o runtime.

**5. Justificativa da VM e da SKU (30s)**
`Standard_B2ats_v2`: 2 vCPU, 1 GiB RAM, burstable — suficiente para uma API
pequena com poucos acessos simultaneos, de baixo custo (~US$ 6,86/mes
de compute; ~US$ 13/mes no total). A B1s nao esta liberada na assinatura
Azure for Students (ver docs/DEPLOY_AZURE_REAL.md).

**6. Armazenamento SQLite (1 min)**
Arquivo unico em disco persistente (`/var/lib/api-tarefas/tarefas.db`),
sem necessidade de servidor de banco separado. Mostrar o Diagrama 3
(modelo ER).

**7. Demonstracao: cadastro (1 min)**
Abrir Swagger, executar `POST /tarefas`, mostrar o HTTP 201.

**8. Demonstracao: consulta (30s)**
`GET /tarefas/{id}` com o mesmo id, mostrando os dados retornados.

**9. Demonstracao: persistencia (1 min)**
Reiniciar a aplicacao (ou a VM, se ao vivo) e mostrar que os dados
continuam la.

**10. GitHub (30s)**
Mostrar o repositorio publicado, o historico de commits, o README.

**11. Testes (30s)**
Mostrar a execucao do `pytest` com o resultado real obtido (19 testes
aprovados).

**12. Conclusao (30s)**
Resumir o que foi efetivamente implementado e demonstrado, sem
extrapolar (ex.: "a aplicacao foi implementada, testada localmente com
19 testes automatizados aprovados, e [preencher: implantada / preparada
para implantacao] na Azure").

---

## Perguntas frequentes e respostas objetivas

**O que e uma API REST?**
Uma interface que permite a comunicacao entre sistemas pela internet
usando o protocolo HTTP, com operacoes padronizadas (GET, POST, PUT,
DELETE) sobre recursos identificados por URLs (ex.: `/tarefas/1`).

**Por que utilizou Python?**
Linguagem com sintaxe simples, grande ecossistema para APIs web, e
adequada ao nivel do projeto academico e ao tempo disponivel.

**Por que escolheu FastAPI?**
Gera documentacao Swagger/OpenAPI automaticamente, tem validacao de
dados integrada via Pydantic, e desempenho adequado com Uvicorn, com
curva de aprendizado baixa.

**Por que SQLite em vez de MySQL/PostgreSQL?**
Nao exige um servidor de banco separado, nao gera custo de
infraestrutura adicional, e e suficiente para o volume de dados e
acessos deste projeto academico. Nao e indicado para producao com
muitos acessos simultaneos de escrita.

**O que e um SKU?**
E o "tamanho" (configuracao de hardware) de uma VM na Azure — define
quantidade de vCPUs, memoria RAM, e capacidade de disco/rede.

**Por que escolheu a B2ats_v2 e nao a B1s?**
A B1s nao esta disponivel na assinatura Azure for Students, e a politica
so permite algumas regioes. A B2ats_v2 (northcentralus) foi a SKU
permitida, com cota, de menor custo — adequada para uma API de baixo trafego.

**Qual a diferenca entre VM e App Service?**
A VM (IaaS) exige que voce instale e gerencie o sistema operacional,
dependencias e servidor web manualmente. O App Service (PaaS) e um
servico gerenciado onde a Azure cuida do sistema operacional e do
runtime, e voce apenas publica o codigo.

**O que acontece se desligar a aplicacao?**
O servico (Uvicorn/FastAPI) para de responder, mas o arquivo SQLite
permanece intacto no disco. Nenhum dado e perdido.

**O que acontece se reiniciar a VM?**
Como o servico foi registrado com `systemctl enable`, ele inicia
automaticamente apos o boot, e o banco de dados (no disco persistente)
continua com todos os registros.

**Onde os dados ficam armazenados?**
Em um arquivo `.db` dentro do disco gerenciado (Managed Disk) da VM, no
caminho `/var/lib/api-tarefas/tarefas.db`.

**O banco de dados fica na nuvem?**
Fica armazenado no disco da VM que esta hospedada na nuvem Azure, mas
nao e um servico de banco de dados gerenciado (como Azure SQL Database)
— e um arquivo SQLite local a maquina virtual.

**Qual o papel do Nginx?**
Atua como proxy reverso: recebe as requisicoes HTTP/HTTPS publicas
(portas 80/443) e as repassa internamente para o Uvicorn, que nunca e
exposto diretamente a internet.

**Qual a diferenca entre Git e GitHub?**
Git e o sistema de controle de versao (ferramenta local que registra o
historico de alteracoes do codigo). GitHub e um servico que hospeda
repositorios Git remotamente, permitindo colaboracao, backup e
publicacao do codigo.

**Como os endpoints foram testados?**
Automaticamente, com Pytest + HTTPX (19 testes cobrindo CRUD,
validacoes, paginacao, codigos HTTP e persistencia), e manualmente,
via Swagger UI e `curl`, seguindo o roteiro em `GUIA_TESTES.md`.

**Como a aplicacao e protegida?**
Rede: NSG restringindo SSH ao IP do administrador e isolando o Uvicorn
da internet (acessivel somente via Nginx). Aplicacao: validacao de
entrada via Pydantic, tratamento de erros sem exposicao de stack
traces, e ausencia de segredos no repositorio. Sem autenticacao de
usuarios (fora do escopo academico definido).

**Como o projeto poderia evoluir para producao?**
Adicionar autenticacao (ex.: OAuth2/JWT), migrar para um banco de dados
gerenciado com suporte a maior concorrencia (ex.: PostgreSQL/Azure
Database), usar HTTPS com certificado valido e dominio proprio,
adicionar monitoramento/alertas, e considerar escalabilidade horizontal
(mais de uma instancia atras de um load balancer).
