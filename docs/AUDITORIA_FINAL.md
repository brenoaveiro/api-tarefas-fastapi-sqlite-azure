# Auditoria final — CyberIncident API

Data: 02/11/2026. Responsável técnico pela revisão: autor do projeto, com apoio de assistente de IA. Escopo: código, banco, testes, implantação na Azure, HTTPS, GitHub, evidências, diagramas, relatório e pacote de entrega. Este documento registra o que foi **verificado**; nada aqui é marcado como feito sem evidência.

## 1. Situação inicial (inspeção)

| Item | Estado encontrado |
|---|---|
| Git | `main` igual a `origin/main` (commit `05a09a1`), árvore limpa; `.gitignore` e os 3 arquivos do Swagger UI estavam rastreados |
| Azure | Assinatura Azure for Students ativa; VM `GS-Cloud-API-VM` em execução; IP público estático `20.80.10.214`; NSG só com as regras 22 (administrador) e 80 |
| API | `/health`, `/`, `/docs`, `/openapi.json` e `/static/dashboard.js` respondendo 200 |
| VM | Commit implantado `61b6288`; `api-tarefas` e `nginx` ativos; Uvicorn só em `127.0.0.1:8000`; 27 GB livres; 887 MB de RAM |
| SQLite | `/var/lib/api-tarefas/tarefas.db` (600, dono `apitarefas`), tabelas `tarefas` e `incidentes` |
| Pacote da etapa anterior | Excluía o pacote do Swagger UI (por minha escolha ao montar o ZIP), o que impedia a execução independente |

O pacote de auditoria externa (`CyberIncident_Auditoria_e_Correcoes.zip`) não estava disponível no ambiente; os dez pontos foram tratados a partir da descrição e verificados contra o repositório e a VM reais.

## 2. Tratamento dos pontos da auditoria anterior

| # | Ponto | Tratamento | Evidência |
|---|---|---|---|
| 1 | Reprodutibilidade incompleta do ZIP | O código do pacote vem de `git archive` do commit (todos os arquivos rastreados). Verificado em ambiente limpo (venv novo, só dependências declaradas) | `05_Testes/ambiente-limpo-*.txt`; testes de entrega |
| 2 | Arquivos do Swagger ausentes | Presentes e íntegros (bundle 1,45 MB, versão 5.17.14, CSS e licença Apache); teste exige existência, tamanho e versão | `tests/test_entrega.py` |
| 3 | `.gitignore` ausente no ZIP | Presente; teste confere os padrões de segredos, bancos e ambientes | `tests/test_entrega.py` |
| 4 | Erro auxiliar de SQLite no script de produção | Reescrito: tabelas verificadas em `sqlite_master`, comandos SQL separados de metacomandos, `PRAGMA` isolados | `scripts/testar_producao.sh` |
| 5 | Contagem de verificações sem os erros auxiliares | Falhas de SSH, SQLite e JSON são contabilizadas; POST que falha interrompe o bloco dependente; limpeza por `trap`; código de saída correto. Teste negativo: 13 falhas e saída 1 | log de produção e teste negativo |
| 6 | Documentação desatualizada sobre HTTPS em IP | Conferida na documentação oficial (Let's Encrypt, 2026, e Certbot) e reescrita | relatório 8; `DEPLOY_AZURE_REAL.md` 6 |
| 7 | Ausência de HTTPS | Implementado: certificado Let's Encrypt para o IP, Certbot 5.9, perfil `shortlived`, webroot; teste em staging antes do real; renovação automática (timer + hook) comprovada com uma renovação forçada (série do certificado mudou sem ação manual) | `deploy/https_ip.sh`; log de produção; Figuras 05, 06, 07 |
| 8 | Ausência de autenticação | Avaliada: para dados fictícios com leitura pública, a restrição de escrita por IP no Nginx (nas portas 80 e 443) é suficiente para a demonstração; autenticação improvisada seria pior. Limitação documentada e evolução proposta (token de API sobre HTTPS) | relatório 9 e 14 |
| 9 | Revisão final entre código, evidências, documentação e implantação | Feita (seções 5 a 8 deste documento) | este arquivo |
| 10 | Demonstrar o aprendizado | `docs/DEFESA_ORAL.md`: 24 perguntas, extras e roteiro de 5 a 10 minutos, ligados ao código e à infraestrutura reais | `DEFESA_ORAL.md` |

### Defeitos adicionais encontrados nesta revisão

- **Vulnerabilidades em dependência:** a `pip-audit` apontou 14 vulnerabilidades no Starlette 0.41.3 (via FastAPI 0.115.6). Atualizados FastAPI 0.162.0 e Starlette 1.10.0 (com Pydantic 2.14.2, SQLAlchemy 2.0.55 e Uvicorn 0.54.0), todos testados; a auditoria atual não encontra vulnerabilidades.
- **Aviso de depreciação nos testes:** o cliente de testes do Starlette recomendava `httpx2`; a troca eliminou o aviso (96 testes, zero avisos).
- **Backup inoperante no deploy (etapa anterior):** `backup.sh` não era executável e o `deploy.sh` apenas avisava. Corrigido: usa `bash` e aborta se o backup falhar.
- **Sincronização do Nginx:** o `deploy.sh` agora instala a configuração, valida com `nginx -t` e restaura a anterior se falhar.
- **Dependência de desenvolvimento com versão não verificada:** uma versão do Pillow que eu havia fixado sem conferir foi substituída pela versão realmente instalada e testada (13.0.0).
- **Textos da interface:** a descrição do Swagger e o rodapé do dashboard foram atualizados para refletir o HTTPS.

## 3. Verificações executadas

| Verificação | Resultado |
|---|---|
| `pytest` local | 96 aprovados, 0 falhas, 0 avisos, 0 ignorados |
| `pyflakes` | sem problemas |
| `pip-audit` | nenhuma vulnerabilidade conhecida |
| GitHub Actions (CI) | `success` nos três últimos commits (instalação limpa + arquivos essenciais + pytest) |
| Produção (`REQUIRE_HTTPS=1`) | 58 verificações, 58 aprovadas, 0 falhas, saída 0 |
| Teste negativo do script | SSH inválido de propósito: 13 falhas contabilizadas e saída 1; nenhum resíduo `[TESTE]` no banco |
| HTTPS | `curl` e Chrome validam a cadeia; SAN com o IP; `/docs` e `/` sem erros de console; escrita via 443 retorna 403 para IP não autorizado |
| Renovação | `certbot renew --dry-run` aprovado; renovação forçada real com troca do certificado servido pelo hook |
| SQLite na VM | `integrity_check ok`, WAL, tabelas `incidentes` e `tarefas` presentes (`sqlite_master`), permissão 600 |
| Backup antes de mudar | `.backup` do SQLite com `integrity_check ok` (tabelas e 9 incidentes); cópia do Nginx e do `.env` |
| Persistência | Serviço reiniciado; incidente idêntico antes e depois (Figura 16) |
| Ambiente limpo (ZIP) | ZIP íntegro; arquivos necessários presentes; nenhum segredo; venv novo; `pip install -r requirements-dev.txt`; 96 testes aprovados; 15 endpoints e POST validados com a aplicação em execução |

A verificação em ambiente limpo foi executada em duas passagens sobre o ZIP: na versão preliminar (log em `05_Testes`) e na versão final, depois de acrescentar os logs e este documento.

## 4. Código e API (revisão)

Revisados: códigos HTTP, validação, paginação e filtros, IP, registros inexistentes, timestamps, transições de status e `resolvido_em`, estatísticas, consistência após criar, atualizar e excluir, ausência de exceções internas expostas, compatibilidade entre ORM, schemas, dashboard e Swagger, banco vazio e com dados, XSS (dashboard usa `textContent` e CSP), injeção de SQL (ORM parametrizado) e CORS (fechado). Nenhum defeito funcional foi encontrado na API; as alterações no código da aplicação foram apenas textuais (HTTPS) e de dependências. O design não foi alterado.

## 5. Auditoria das 18 evidências

| Fig. | Conteúdo | Decisão | Motivo |
|---|---|---|---|
| 01 | Resource Group | Mantida | Recursos e região inalterados |
| 02 | Máquina virtual | Mantida | VM em execução, dados corretos |
| 03 | SKU (tela Size) | Mantida | Mostra `Current size Standard_B2ats_v2` |
| 04 | Armazenamento | Mantida | Disco Standard SSD LRS 32 GiB inalterado |
| 05 | Rede | **Refeita** | A lista de regras do NSG ganhou a regra de HTTPS |
| 06 | NSG | **Refeita** | Mostra a nova regra `allow-https` (443) |
| 07 a 13 | Dashboard, Swagger e chamadas | **Refeitas** | URL agora HTTPS e textos finais da interface |
| 14 | Serviço systemd | **Refeita** | Estado do serviço após o deploy final |
| 15 | SQLite | **Refeita** | Estado final do banco |
| 16 | Persistência | **Refeita** | Usa `curl` via HTTPS e novo reinício |
| 17 | GitHub | **Refeita** | Repositório com README, descrição e commits finais |
| 18 | Pytest | **Refeita** | 96 testes, sem avisos |

Todas as 18 foram abertas e inspecionadas: legíveis, sem dados sensíveis (IP do administrador, ID da assinatura e e-mail mascarados), coerentes com a legenda e com resultados reais. As capturas de console são janelas reais; o prompt é o do computador local porque o SSH roda dele. Nenhuma imagem foi montada ou fabricada. Os originais ficam em `Print_GS`; as cópias do relatório e do pacote têm o e-mail da conta mascarado (edição apenas para ocultar dados).

## 6. Diagramas

Os seis diagramas foram revisados contra o código e a infraestrutura reais e atualizados: HTTPS e NSG com 80/443 (1 e 2), modelo de dados (3), fluxo de cadastro e status (4), CI no fluxo de deploy (5) e 96 testes, 58 verificações e CI (6). Os fluxos largos passaram à orientação vertical e as margens foram aparadas para ficarem legíveis no Word e no PDF. Nenhum componente inexistente é representado.

## 7. Documentação

Relatório com 16 seções, no formato exigido (A4, Arial 11, preto, justificado, capa em preto e branco, sem cabeçalho, rodapé nem numeração), confirmado pelo próprio Word: 31 páginas, cabeçalho e rodapé vazios, sem numeração, todos os parágrafos em Arial preta. Todas as páginas do PDF foram inspecionadas. O Word e o PDF são gerados do mesmo texto-fonte (`RELATORIO_TECNICO.md`). Documentos atualizados: README, deploy real, guia de testes, guia de evidências, apresentação, defesa oral e matriz de conformidade.

## 8. Nota final pela rubrica

| Critério | Peso | Nota | Justificativa e desconto |
|---|---|---|---|
| Implementação e funcionamento da API | 25% | 9,5 | Completa, validada e testada; escopo propositalmente simples (sem autenticação de usuários) |
| SQLite, modelagem e persistência | 15% | 9,5 | Restrições, índices, WAL, migração segura e persistência comprovada; SQLite limita a escala |
| Azure e infraestrutura | 20% | 9,3 | Recursos explicados e verificados, HTTPS real com renovação comprovada; VM única de 1 GiB e backups no mesmo disco |
| Testes e reprodutibilidade | 15% | 9,7 | 96 testes sem avisos, CI, 58 verificações em produção, teste negativo e ambiente limpo; as capturas do Portal exigem login manual |
| Documentação e evidências | 15% | 9,4 | Relatório detalhado, 18 evidências reais e matriz de conformidade; evidências de console são janelas reais, mas com um prompt do computador local |
| Segurança e limitações | 10% | 8,8 | Controles em camadas e limitações honestas; sem autenticação de usuários, escrita depende de IP estável e certificado de IP é de curta duração |

**Nota ponderada: 9,4 / 10.** Não se atribui 10 porque restam limitações reais (autenticação, certificado de curta duração, VM única), todas documentadas e inerentes ao escopo e ao orçamento do trabalho.

## 9. Pendências reais

- Nenhuma pendência bloqueante. Limitações aceitas e documentadas: ver a seção 14 do relatório.
- O certificado de IP dura cerca de seis dias. Se a VM for desalocada por mais tempo, o HTTPS ficará inválido até o timer renovar após a próxima inicialização (o HTTP segue funcionando).
- Os prints do Portal Azure só podem ser refeitos com login manual.
