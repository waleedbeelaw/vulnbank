# Security Architecture

Architecture views for VulnBank on **`vulnerable-lab`**: runtime application stack and DevSecOps pipeline.

## Runtime architecture

VulnBank is a Flask REST API with JWT authentication, a service layer for transfers, SQLAlchemy ORM, and PostgreSQL. Security audit events and request correlation IDs are emitted from the application layer.

```mermaid
flowchart TB
    subgraph Client["Client (localhost / lab)"]
        C[HTTP Client]
    end

    subgraph Docker["Docker Compose boundary"]
        subgraph AppContainer["app container (non-root vulnbank user)"]
            API[Flask API]
            AuthN[JWT authentication]
            AuthZ[Authorization checks]
            SVC[Transaction service layer]
            ORM[SQLAlchemy ORM]
            LOG[Security audit logging<br/>JSON + X-Request-ID]
            API --> AuthN
            API --> AuthZ
            API --> SVC
            SVC --> ORM
            API --> LOG
        end

        subgraph DBContainer["db container"]
            PG[(PostgreSQL)]
        end

        ORM --> PG
    end

    C -->|"HTTP :5000 (host published)"| API

    note1["PostgreSQL port 5432<br/>NOT exposed to host"]
    DBContainer -.-> note1
```

### Runtime security properties

| Property | Implementation |
|----------|----------------|
| Authentication | JWT (`Authorization: Bearer`) on protected routes |
| Authorization | Object-level checks (accounts, transactions, users) |
| Financial integrity | DB transactions, row locking, Decimal types |
| Secrets | `JWT_SECRET_KEY`, `DATABASE_URL` via environment - not in Git |
| Audit trail | `vulnbank.security` JSON logger; no passwords/JWTs in logs |
| Request tracing | `X-Request-ID` (client or server UUID) |
| Database exposure | Internal Compose network only |
| Container identity | `USER vulnbank` in Dockerfile |

See [security-logging.md](security-logging.md), [container-security.md](container-security.md), [deployment-security.md](deployment-security.md).

## DevSecOps pipeline architecture

Changes flow through feature branches and pull requests into the protected **`vulnerable-lab`** branch after eight required security gates pass.

```mermaid
flowchart LR
    DEV[Developer]
    FB[Feature branch]
    PR[Pull Request]
    PL[vulnerable-lab<br/>protected branch]

    DEV --> FB --> PR --> PL

    subgraph Gates["8 PR Security Gates (parallel jobs)"]
        G1[pytest]
        G2[Bandit SAST]
        G3[pip-audit SCA]
        G4[Gitleaks]
        G5[OWASP ZAP DAST]
        G6[Trivy container]
        G7[Syft SBOM]
        G8[Checkov IaC]
    end

    PR --> Gates
    Gates -->|all pass| PL

    subgraph Artifacts["Security artifacts (where applicable)"]
        ZAP[ZAP reports<br/>on DAST failure]
        SBOM[CycloneDX SBOM<br/>vulnbank-sbom-cyclonedx]
    end

    G5 -.-> ZAP
    G7 -.-> SBOM
```

### Gate summary

| # | Job name | Tool | Primary focus |
|---|----------|------|---------------|
| 1 | PR Security Gate - Test Suite (pytest) | pytest | Functional + security regression (125 tests) |
| 2 | PR Security Gate - SAST (Bandit) | Bandit | Python source anti-patterns |
| 3 | PR Security Gate - SCA (pip-audit) | pip-audit | Declared dependency CVEs |
| 4 | PR Security Gate - Secret Scan (Gitleaks) | Gitleaks v3 | Git history secrets |
| 5 | PR Security Gate - DAST (OWASP ZAP) | OWASP ZAP | Passive baseline + authenticated regression |
| 6 | PR Security Gate - Container Scan (Trivy) | Trivy | Fixable HIGH/CRITICAL image CVEs |
| 7 | PR Security Gate - SBOM (Syft) | Syft | CycloneDX JSON from **built image** |
| 8 | PR Security Gate - IaC Scan (Checkov) | Checkov | Dockerfile + Compose configuration |

Pipeline hardening: SHA-pinned actions, workflow `contents: read`, concurrency cancellation, job timeouts - see [cicd-security.md](cicd-security.md).

Workflow definition: [`.github/workflows/security.yml`](../.github/workflows/security.yml).

## Related documentation

- [threat-model.md](threat-model.md)
- [security-journey.md](security-journey.md)
- [supply-chain-security.md](supply-chain-security.md)
