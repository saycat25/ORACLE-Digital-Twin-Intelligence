# ORACLE — Digital Twin Intelligence

**Gêmeo digital empresarial de infraestrutura para modelagem de dependências, simulação controlada de falhas e análise explicável de impacto.**

> **Status:** em desenvolvimento ativo. Este repositório ainda não é certificado nem deve ser considerado pronto para produção. Confira o estado real da implementação e as notas de segurança antes de implantar.

## O que é

O ORACLE representa uma infraestrutura como um grafo direcionado. Os nós representam serviços ou componentes; as arestas representam relações de consumidor para dependência. O motor atual percorre as dependências reversas a partir de um componente com falha e calcula pontuações determinísticas de impacto ponderadas pela criticidade.

## Implementado nesta versão

- API REST com FastAPI para componentes, dependências e simulações.
- Persistência SQLAlchemy, com SQLite por padrão e suporte a PostgreSQL.
- Motor determinístico e explicável de análise de impacto.
- Base de console web em React + TypeScript.
- Ambiente de desenvolvimento com Docker Compose.
- Testes com Pytest e análise estática com Ruff na integração contínua.
- Documentação em português e inglês.

## Capacidades empresariais planejadas

Os itens abaixo são objetivos de desenvolvimento e não devem ser considerados implementados até que existam código e testes correspondentes: OIDC/SSO, isolamento multi-tenant, RBAC granular, trilha de auditoria imutável, ingestão de telemetria, métricas e traces OpenTelemetry, topologia temporal, explicações assistidas por IA, limitação de requisições, testes de carga e segurança, SBOM e releases assinadas.

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
