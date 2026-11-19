# ORACLE — Digital Twin Intelligence

**Gêmeo digital empresarial de infraestrutura para modelagem de dependências, simulação controlada de falhas e análise explicável de impacto.**

> **Status:** em desenvolvimento ativo. Este repositório ainda não é certificado nem deve ser considerado pronto para produção. Confira o estado real da implementação e as notas de segurança antes de implantar.

## O que é

O ORACLE representa uma infraestrutura como um grafo direcionado. Os nós representam serviços ou componentes; as arestas representam relações de consumidor para dependência. O motor atual percorre as dependências reversas a partir de um componente com falha e calcula pontuações determinísticas de impacto ponderadas pela criticidade.

## Implementado nesta versão

- API REST com FastAPI para componentes, dependências, topologia e simulações.
- Endpoint de ingestão e consulta de amostras de telemetria por componente/métrica.
- Trilha básica de auditoria para criação de componentes, dependências, simulações e ingestão de telemetria.
- Métricas HTTP em formato compatível com Prometheus, protegidas pelo papel `admin`, e traces OpenTelemetry opcionais com exportação OTLP.
- Exportação JSON da auditoria por tenant, restrita ao papel `admin`.
- Exportação da topologia atual como snapshot JSON pela API.
- Planejamento de capacidade com carga atual, capacidade nominal e projeção por multiplicador de demanda.
- Histórico temporal por tenant, com snapshots automáticos após cada criação de componente ou dependência e consulta de versões antigas.
- Comparação determinística de dois cenários com lista de impactos exclusivos/compartilhados e variação de pontuação.
- Explicação opcional de simulações via DeepSeek, protegida por opt-in explícito no servidor.
- Comparação e análise assistida disponíveis na API documentada em `/docs`.
- Persistência SQLAlchemy, com SQLite por padrão e suporte a PostgreSQL.
- Motor determinístico e explicável de análise de impacto.
- Console web com cadastro de componentes/dependências, grafo SVG, simulações simples e comparativas, telemetria, auditoria e conexão por chave de API na sessão.
- Ambiente de desenvolvimento com Docker Compose.
- Pytest, Ruff, pip-audit, CodeQL e geração de SBOM CycloneDX na integração contínua.
- Workflow de release por tag, com pacotes Python/frontend e atestação de procedência GitHub/Sigstore.
- Scripts de backup/restauração PostgreSQL com verificação SHA-256 e manual operacional.
- Documentação em português e inglês.

## Limites e próximas fases

O isolamento por tenant, o controle de acesso por papéis, a ingestão de telemetria e a trilha de auditoria estão implementados em nível inicial. As rotas exigem papéis adequados quando `ORACLE_API_KEYS` está configurado; o papel `ingestor` ou `admin` pode enviar telemetria. A assistência DeepSeek exige `DEEPSEEK_API_KEY` e `AI_DATA_SHARING_ENABLED=true`; por padrão, o compartilhamento de dados com provedores externos fica desativado. O tenant é obtido da credencial validada; `X-Tenant-ID`, quando enviado, serve apenas como conferência e valores divergentes são rejeitados.

Ainda faltam OIDC/SSO, provisionamento/rotação/revogação gerenciada de chaves, armazenamento de auditoria à prova de adulteração e políticas de retenção, alertas/SLOs, traces de negócio mais detalhados, reprodução/diff temporal avançado e modelos de capacidade, histórico administrativo mais completo, testes de carga/penetração, simulações periódicas de restauração, retenção externa de backups e revisão de segurança independente. A atestação assinada só será criada quando uma tag de versão acionar o workflow de release. Execute `alembic upgrade head` antes de iniciar a API. A migração atribui dados legados ao tenant `default`. Consulte o [roadmap](docs/ROADMAP.md) para o estado atualizado.

## Instalação rápida

Requer Python 3.11 ou superior.

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
# Linux/macOS:
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn oracle_api.main:app --reload
```

Documentação da API: http://127.0.0.1:8000/docs

## Docker

```bash
docker compose up --build
```

## Executar testes

```bash
cd backend
pytest
ruff check .
```

## Segurança e uso responsável

O simulador atual executa apenas cálculos sobre o grafo; não realiza alterações na infraestrutura. Utilize dados sintéticos. Não conecte esta versão de desenvolvimento a sistemas de produção sem revisão de segurança independente, integração de identidade empresarial (OIDC/SSO), gestão de chaves, trilha de auditoria à prova de adulteração, procedimentos de backup/restauração e testes operacionais.

## Documentação

- [Documentação em inglês](README.md)
- [Política de segurança](SECURITY.md)
- [Modelo de ameaças](docs/THREAT_MODEL.md)
- [Manual operacional](docs/OPERATIONS.md)
- [Como contribuir](CONTRIBUTING.md)
- [Licença e atribuição](LICENSE) e [NOTICE](NOTICE)

## Direitos autorais, licença e atribuição obrigatória

O ORACLE utiliza a **ORACLE Attribution License (OAL) 1.0**. O uso, a modificação e a redistribuição são gratuitos, inclusive para fins comerciais, desde que:

1. O aviso de direitos autorais e o texto da licença sejam preservados.
2. Seja dado crédito claro ao projeto original.
3. Seja incluído um link clicável para o repositório original:
   https://github.com/saycat25/ORACLE-Digital-Twin-Intelligence
4. Versões modificadas sejam identificadas como modificadas e não sugiram endosso dos autores originais.

Esta é uma licença personalizada com exigência de atribuição. **Não é MIT, Apache-2.0 nem uma licença aprovada pela Open Source Initiative (OSI)**. Consulte o arquivo [LICENSE](LICENSE) para os termos completos. Dependências de terceiros mantêm suas próprias licenças.
