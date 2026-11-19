# Security Policy

## Supported versions

The project is under active development. No release is currently designated production-supported.

## Reporting a vulnerability

Do not publish exploitable details in public issues. Contact the repository maintainer privately through the GitHub profile/contact channel and include affected commit/version, impact, reproduction steps, and any safe proof of concept. Do not include real credentials or customer data.

## Deployment warning

Although baseline API-key authentication, role checks and tenant filtering are implemented, the project is not production-certified. OIDC/SSO, managed key lifecycle, tamper-evident audit storage, retention controls, load/penetration testing, backup/restore drills and independent security review remain open. Use a trusted environment and synthetic data until these controls are completed. Never expose development mode directly to the public internet.


## Tenant credentials and roles

Configure ORACLE_API_KEYS as semicolon-separated token|tenant-id|role entries. Keep these values in a secret manager; never commit live credentials. Production startup is blocked when the registry is empty. Rotate credentials by deploying a replacement registry and removing old entries. OIDC/SSO and self-service credential lifecycle are not yet implemented.
