# ORACLE Threat Model — Initial Baseline

## Scope

This document describes the current development foundation: REST API, relational persistence, dependency graph, simulation engine, and starter web console.

## Assets

- Infrastructure topology and dependency metadata.
- Simulation inputs and results.
- Database integrity and availability.
- Deployment configuration and secrets.

## Trust boundaries

- Browser to API (HTTP boundary).
- API process to database (credential and network boundary).
- CI runner to repository and package registries.
- Operator-managed environment variables and container configuration.

## Threats to address

| Threat | Potential impact | Required mitigation |
|---|---|---|
| Unauthenticated API exposure | Unauthorized topology disclosure or modification | OIDC, authorization, network controls |
| Cross-tenant data access | Tenant data leakage | Tenant-scoped queries, database constraints, isolation tests |
| Malicious or oversized input | Resource exhaustion or invalid graph state | Validation, request limits, timeouts |
| Database credential exposure | Data compromise | Secret manager, rotation, least privilege |
| Dependency compromise | Supply-chain compromise | Pinned/managed dependencies, SBOM, scanning |
| Audit tampering | Loss of accountability | Append-only audit design and protected retention |
| Unsafe operational integration | Real service disruption | Read-only integrations by default, explicit approvals |

## Current limitations

The initial API does not yet implement user authentication, RBAC, tenant isolation, immutable audit logs, rate limiting, or production-grade secret management. CORS is not an authentication mechanism. The simulation engine is analytical and does not validate real-world service behavior.

## Release gate

A production claim requires implemented controls, automated security tests, load tests, backup/restore validation, operational documentation, and independent review. This threat model must be updated when the architecture changes.
