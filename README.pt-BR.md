# ORACLE — Digital Twin Intelligence

**Plataforma de gêmeos digitais para modelar infraestrutura de software, simular falhas controladas e analisar o impacto entre dependências.**

> O ORACLE está sendo desenvolvido em etapas. Esta versão contém a primeira base executável: modelo tipado de infraestrutura, mecanismo determinístico de análise de impacto, API FastAPI, persistência, testes, configuração Docker e início do painel React. Funcionalidades do roadmap não são consideradas implementadas até que tenham código e testes correspondentes.

## Ideia central

O ORACLE representa um ambiente como um grafo direcionado:

- **Nós** representam serviços, bancos de dados, filas, APIs ou componentes de infraestrutura.
- **Arestas** representam dependências e sua criticidade.
- **Cenários** descrevem degradação ou indisponibilidade controlada de um componente.
- **Resultados** estimam quais componentes dependentes podem ser afetados, usando alcançabilidade no grafo e criticidade das dependências.

O mecanismo inicial é determinístico e explicável. Ele ainda não prevê interrupções reais nem aprende o comportamento do ambiente a partir de telemetria.

## Recursos implementados nesta base

- Criar e listar componentes da infraestrutura.
- Criar e listar dependências direcionadas.
- Executar simulação determinística de impacto a partir de um componente.
- Persistir topologia e resultados em SQLite por padrão; PostgreSQL pode ser usado por `DATABASE_URL`.
- Disponibilizar endpoints de saúde e API.
- Executar testes automatizados.
- Subir API e banco com Docker Compose.

## Arquitetura

```text
Painel React + TypeScript
          |
          v
       API FastAPI
          |
          +---- Domínio / mecanismo de grafos
          |
          +---- Repositórios SQLAlchemy
                       |
                 SQLite / PostgreSQL
```

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

Acesse `http://127.0.0.1:8000/docs`.

## Testes

```bash
cd backend
pytest
```

## Docker

Na raiz do repositório:

```bash
docker compose up --build
```

API: `http://localhost:8000`  
OpenAPI: `http://localhost:8000/docs`

## Configuração

Copie `.env.example` para `.env`.

| Variável | Padrão | Descrição |
|---|---|---|
| `ORACLE_ENV` | `development` | Ambiente de execução |
| `DATABASE_URL` | `sqlite:///./oracle.db` | URL do banco SQLAlchemy |
| `API_PREFIX` | `/api/v1` | Prefixo versionado da API |
| `CORS_ORIGINS` | `http://localhost:5173` | Origens permitidas, separadas por vírgula |

Nunca publique credenciais reais ou segredos de infraestrutura.

## Endpoints

| Método | Endpoint | Finalidade |
|---|---|---|
| GET | `/health` | Verificação de disponibilidade |
| POST | `/api/v1/nodes` | Criar componente |
| GET | `/api/v1/nodes` | Listar componentes |
| POST | `/api/v1/edges` | Criar dependência |
| GET | `/api/v1/edges` | Listar dependências |
| POST | `/api/v1/simulations` | Executar simulação de impacto |
| GET | `/api/v1/simulations/{id}` | Consultar simulação |

## Segurança e operação

- Esta primeira versão é uma base de desenvolvimento, não uma implantação pronta para produção.
- Não conecte o sistema a infraestrutura de produção nem execute ações disruptivas.
- As simulações calculam impacto no grafo e não alteram infraestrutura.
- Autenticação, autorização, isolamento entre organizações, trilha de auditoria imutável, ingestão de telemetria e endurecimento para produção estão no roadmap.
- Utilize dados sintéticos até que os controles de segurança e os procedimentos operacionais sejam revisados.

## Roadmap

1. **Fundação (atual):** modelo de topologia, simulação determinística, API REST, persistência, testes e contêineres.
2. **Controles empresariais:** OIDC/OAuth2, RBAC, isolamento multi-tenant, trilha de auditoria e limites de API.
3. **Observabilidade:** ingestão de métricas, traces e logs via OpenTelemetry, normalização de eventos e descoberta de topologia.
4. **Evolução do gêmeo digital:** estado temporal, modelos de capacidade e falhas em cascata.
5. **Análise assistida por IA:** provedor DeepSeek opcional para explicações e resumos, mantendo os resultados determinísticos como fonte da verdade.
6. **Console web:** visualização da topologia, criação de cenários, histórico e governança.
7. **Confiabilidade:** testes de carga, modelo de ameaças, SBOM, releases assinadas e CI.

## Contribuição e licença

Consulte [CONTRIBUTING.md](CONTRIBUTING.md). Licença MIT em [LICENSE](LICENSE).
