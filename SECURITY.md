# Security Policy

## Supported versions

The project is under active development. No release is currently designated production-supported.

## Reporting a vulnerability

Do not publish exploitable details in public issues. Contact the repository maintainer privately through the GitHub profile/contact channel and include affected commit/version, impact, reproduction steps, and any safe proof of concept. Do not include real credentials or customer data.

## Deployment warning

Until authentication, authorization, tenant isolation, secrets management, audit controls, and deployment hardening are implemented and independently reviewed, run only in a trusted development environment with synthetic data. Never expose the development API directly to the public internet.


## Tenant credentials and roles

Configure ORACLE_API_KEYS as semicolon-separated token|tenant-id|role entries. Keep these values in a secret manager; never commit live credentials. Production startup is blocked when the registry is empty. Rotate credentials by deploying a replacement registry and removing old entries. OIDC/SSO and self-service credential lifecycle are not yet implemented.
