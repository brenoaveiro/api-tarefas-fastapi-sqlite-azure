# Defesa oral — CyberIncident API

Respostas curtas e tecnicamente corretas, ligadas ao código e à infraestrutura reais deste projeto. Use as suas próprias palavras: o objetivo é entender, não decorar.

## Roteiro de demonstração (5 a 10 minutos)

1. **Contexto (45 s).** Um SOC registra e acompanha incidentes de segurança. A CyberIncident API simula esse registro com dados fictícios.
2. **Arquitetura (1 min).** Diagrama 1: navegador → IP público → NSG → rede virtual → Nginx → Uvicorn/FastAPI → SQLite no disco gerenciado.
3. **Azure (1,5 min).** Portal: Resource Group `GS_Cloud_API`, VM `GS-Cloud-API-VM` (`Standard_B2ats_v2`, 2 vCPU, 1 GiB), disco Standard SSD de 32 GiB, VNet, NSG e IP público.
4. **Dashboard e Swagger (1,5 min).** `https://20.80.10.214/` e `/docs`: números vindos do SQLite; tema próprio.
5. **Cadastro, consulta, status e estatísticas (2 min).** `POST` (201), `GET` (200), `PATCH` para `em_analise` e tentativa inválida (422), `GET /incidentes/estatisticas`.
6. **Persistência (45 s).** Reiniciar o serviço (`systemctl restart api-tarefas`) e consultar o mesmo incidente.
7. **GitHub, testes e HTTPS (1 min).** Repositório e CI aprovado; `python -m pytest -q` (96 testes); cadeado do HTTPS no navegador.
8. **Conclusão (30 s).** O que foi comprovado e as limitações.

> A escrita (POST e PATCH) só funciona do IP autorizado; de outras redes a resposta é 403. Peça a liberação do IP antes de apresentar de outro lugar.

## As 24 perguntas

**1. O que é uma API REST?** Uma interface em que o cliente acessa recursos (aqui, incidentes) por endereços HTTP e métodos (GET, POST etc.), trocando dados em JSON. Cada requisição é independente e a resposta traz um código que informa o resultado.

**2. Por que Python?** Pela legibilidade, pelo ecossistema para web e pela facilidade de testar. Todo o código da API (`app/`) e os testes (`tests/`) são em Python.

**3. Por que FastAPI?** Porque valida os dados e gera a documentação (OpenAPI/Swagger) a partir dos mesmos tipos Python, o que evita código repetido e erros. Está em `app/main.py`.

**4. Qual é o papel do Uvicorn?** É o servidor que executa a aplicação FastAPI: abre a porta, entende HTTP e chama o código. Aqui escuta só em `127.0.0.1:8000`, invisível para a internet.

**5. Qual é o papel do Nginx?** É a porta de entrada: recebe as conexões nas portas 80 e 443, faz o HTTPS, repassa as requisições ao Uvicorn (proxy reverso) e bloqueia escrita de IPs não autorizados.

**6. Como o SQLite armazena informações?** Em um único arquivo (`/var/lib/api-tarefas/tarefas.db`) com tabelas, índices e dados. Não precisa de servidor de banco. Usa o modo WAL para reduzir bloqueios entre leitura e escrita.

**7. O que é SQLAlchemy?** Um ORM: traduz objetos Python (`Incidente`) em comandos SQL e o inverso. Como usa parâmetros, evita injeção de SQL. Está em `app/models.py` e `app/crud.py`.

**8. Como o Pydantic valida dados?** Cada campo tem tipo e regras (tamanhos, valores permitidos, IP válido). Se algo não cumpre, a API devolve 422 antes de tocar no banco. Está em `app/schemas.py` e `app/enums.py`.

**9. Qual a diferença entre GET, POST, PUT, PATCH e DELETE?** GET consulta; POST cria; PUT substitui todos os campos; PATCH altera só uma parte (aqui, o status); DELETE remove.

**10. O que são códigos HTTP?** Números que resumem o resultado: 200 (ok), 201 (criado), 204 (removido, sem corpo), 404 (não encontrado), 422 (dados inválidos), 403 (proibido, usado no bloqueio de escrita) e 500 (erro interno).

**11. O que é uma VM?** Um computador virtual que roda sobre o hardware da Azure; aqui, um Linux Ubuntu 24.04 em que instalamos Nginx, Python e a aplicação.

**12. O que é SKU?** O "tamanho" da VM (e o código que identifica o produto). Define vCPU, RAM e preço. A nossa é a `Standard_B2ats_v2`.

**13. Por que a B2ats_v2?** A primeira escolha, `Standard_B1s`, não está disponível na assinatura Azure for Students; a política limita as regiões e outras máquinas tinham cota zero. A B2ats_v2 em North Central US foi a mais barata permitida com cota. É da série B (*burstable*): acumula crédito de CPU em repouso e usa em picos, bom para tráfego baixo.

**14. Qual a diferença entre CPU e RAM?** A CPU (aqui, 2 vCPUs) executa as instruções; a RAM (1 GiB) guarda temporariamente os programas em execução e é muito mais rápida que o disco, mas se perde ao desligar. Com pouca RAM usamos 1 GiB de *swap* no disco.

**15. O que é disco gerenciado?** Um disco virtual cuja infraestrutura a Azure administra e que existe independente da VM. O nosso é Standard SSD LRS de 32 GiB (LRS = três cópias no mesmo datacenter).

**16. Onde está armazenado o SQLite?** Em `/var/lib/api-tarefas/tarefas.db`, dentro do disco gerenciado, com permissão 600 e dono `apitarefas`.

**17. Por que o banco persiste após reiniciar?** Porque os dados estão no arquivo, no disco, e não na memória do processo. Reiniciar o serviço (ou a VM) não apaga o disco. A Figura 16 mostra o mesmo incidente antes e depois.

**18. O que faz o NSG?** É o firewall da Azure: regras por prioridade que permitem ou negam o tráfego. Liberamos SSH só para o IP do administrador e as portas 80 e 443 ao público; o resto é negado (inclusive a 8000).

**19. O que são VNet e subnet?** A VNet é uma rede privada na Azure (10.10.0.0/16); a subnet é uma fatia dela (10.10.1.0/24) onde fica a VM, com o IP privado 10.10.1.4.

**20. Qual o papel do GitHub?** Guardar o histórico do código, permitir a atualização da VM por `git pull` e rodar a integração contínua (GitHub Actions) que testa o projeto em ambiente limpo.

**21. Como funcionam os testes?** O pytest sobe a aplicação com um banco temporário e faz requisições simuladas, verificando respostas e dados (96 testes). Em produção, o `testar_producao.sh` faz 58 verificações na URL pública, inclusive reiniciar o serviço e checar o certificado.

**22. Como o dashboard obtém as estatísticas?** O JavaScript chama `GET /incidentes/estatisticas` e `GET /incidentes`; a API calcula tudo com `GROUP BY` no SQLite. Nenhum número é fixo.

**23. Quais controles de segurança foram implementados?** NSG e SSH restrito; porta 8000 fechada; escrita limitada por IP no Nginx; HTTPS com Let's Encrypt e renovação automática; validação de entrada, consultas parametrizadas, proteção contra XSS e CSP no painel; serviço sem privilégios; segredos fora do GitHub; dependências auditadas.

**24. Quais limitações ainda existem?** Não há autenticação de usuários (a escrita depende do IP); o certificado do IP dura cerca de 6 dias; o SQLite não é indicado para muita escrita simultânea; a VM é única e tem só 1 GiB de RAM; os backups ficam no mesmo disco.

## Perguntas extras prováveis

- **Como o HTTPS funciona sem domínio?** O Let's Encrypt passou a emitir certificados para endereços IP públicos, de curta duração. O Certbot comprova o controle do IP por um arquivo servido na porta 80 (desafio HTTP-01), instala o certificado e renova duas vezes ao dia; um *hook* recarrega o Nginx.
- **Por que não redirecionar HTTP para HTTPS?** O certificado dura poucos dias e a VM pode ficar desligada; o HTTP serve de contingência. Também não usamos HSTS, que prenderia o navegador ao HTTPS.
- **A API tem login?** Não. É um trabalho com dados fictícios, de leitura pública e escrita restrita por IP; uma autenticação improvisada seria pior que nenhuma. A evolução seria um token de API, sempre sobre HTTPS.
- **O que acontece com a tabela de tarefas?** Foi preservada no mesmo arquivo; a aplicação só cria a tabela `incidentes` se ela não existir.
- **E se a atualização falhar?** O `deploy.sh` faz backup antes e aborta se ele falhar; a configuração do Nginx é restaurada se `nginx -t` falhar; dá para voltar ao commit anterior.
