# ORACLE — Digital Twin Intelligence

**Gêmeo digital empresarial de infraestrutura para modelagem de dependências, simulação controlada de falhas e análise explicável de impacto.**

> **Status:** em desenvolvimento ativo. Este repositório ainda não é certificado nem deve ser considerado pronto para produção. Confira o estado real da implementação e as notas de segurança antes de implantar.

## O que é

O ORACLE representa uma infraestrutura como um grafo direcionado. Os nós representam serviços ou componentes; as arestas representam relações de consumidor para dependência. O motor atual percorre as dependências reversas a partir de um componente com falha e calcula pontuações determinísticas de impacto ponderadas pela criticidade.

## Implementado nesta versão

- API REST com FastAPI para componentes, dependências, topologia e simulações.
- Endpoint de ingestão e consulta de amostras de telemetria por componente/métrica.
- Trilha básica de auditoria para criação de componentes, dependências, simulações e ingestão de telemetria.
- Métricas HTTP em formato compatível com Prometheus, protegidas pelo papel `admin`.
- Exportação JSON da auditoria por tenant, restrita ao papel `admin`.
- Exportação da topologia atual como snapshot JSON pela API.
- Comparação determinística de dois cenários com lista de impactos exclusivos/compartilhados e variação de pontuação.
- Explicação opcional de simulações via DeepSeek, protegida por opt-in explícito no servidor.
- Comparação e análise assistida disponíveis na API documentada em `/docs`.
- Persistência SQLAlchemy, com SQLite por padrão e suporte a PostgreSQL.
- Motor determinístico e explicável de análise de impacto.
- Base de console web em React + TypeScript.
- Ambiente de desenvolvimento com Docker Compose.
- Testes com Pytest e análise estática com Ruff na integração contínua.
- Documentação em português e inglês.

## Limites e próximas fases

O isolamento por tenant, o controle de acesso por papéis, a ingestão de telemetria e a trilha de auditoria estão implementados em nível inicial. A variável `INGESTION_API_KEY`, quando configurada, exige `X-API-Key` no endpoint de escrita de telemetria. A assistência DeepSeek exige `DEEPSEEK_API_KEY` e `AI_DATA_SHARING_ENABLED=true`; por padrão, o compartilhamento de dados com provedores externos fica desativado. `X-Tenant-ID` apenas identifica registros de auditoria/telemetria: **não isola** componentes, dependências ou simulações e não é um mecanismo de autenticação.

Ainda faltam OIDC/SSO, provisionamento/rotação/revogação gerenciada de chaves, retenção/exportação e proteção contra adulteração da auditoria, OpenTelemetry, alertas, topologia temporal e modelos de capacidade, integração opcional com DeepSeek além do endpoint de explicação básica, console interativo completo, testes de carga/segurança, SBOM, assinatura de releases e recuperação de backup. Execute `alembic upgrade head` antes de iniciar a API. A migração atribui dados legados ao tenant `default`. Consulte o [roadmap](docs/ROADMAP.md) para o estado atualizado.

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

O simulador atual executa apenas cálculos sobre o grafo; não realiza alterações na infraestrutura. Utilize dados sintéticos. Não conecte esta versão de desenvolvimento a sistemas de produção sem revisão de segurança, autenticação e autorização, isolamento entre organizações, procedimentos de backup/restauração e testes operacionais.

## Documentação

- [Documentação em inglês](README.md)
- [Política de segurança](SECURITY.md)
- [Modelo de ameaças](docs/THREAT_MODEL.md)
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
