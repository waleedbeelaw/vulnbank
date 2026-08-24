# Software Supply-Chain Security

## Purpose

Software supply-chain security ensures that what is **built**, **shipped**, and **run** matches what was reviewed. Dependency declarations, container images, and CI evidence together reduce the risk of undeclared components, vulnerable packages, and unverified artifacts entering the release path.

For VulnBank, supply-chain controls focus on:

- Declared Python runtime dependencies
- Reproducible container packaging
- Point-in-time **Software Bill of Materials (SBOM)** inventory
- Automated vulnerability and secret scanning in CI

An SBOM is **inventory and evidence**. It does not, by itself, prove that software is vulnerability-free.

## Existing controls

These controls complement one another:

| Control | Role |
|---------|------|
| [`requirements.txt`](../requirements.txt) | Declared Python runtime dependencies |
| **pip-audit** | Python dependency vulnerability analysis (SCA) |
| [`Dockerfile`](../Dockerfile) | Reproducible application packaging |
| **Syft** (via Anchore SBOM Action) | Actual container component inventory → CycloneDX SBOM |
| **Trivy** | Container OS/library vulnerability analysis |
| **Gitleaks** | Committed secret detection |
| **GitHub Actions** | Automated enforcement and artifact retention |

```
requirements.txt  →  what we declare
pip-audit         →  are declared Python deps vulnerable?
Dockerfile        →  how the app is packaged
Syft SBOM         →  what is actually in the built image
Trivy             →  are image components vulnerable (fixable gate)?
Gitleaks          →  were secrets committed?
```

## SBOM

### What is an SBOM?

A **Software Bill of Materials** is a structured inventory of components in a software artifact — packages, libraries, and operating-system files discovered in a container image.

### Why CycloneDX?

VulnBank uses **CycloneDX JSON** because it is a widely adopted SBOM standard supported by Syft, Trivy, and many security tools. The CI artifact is named `sbom.cdx.json`.

### Why generate from the container image?

Generating the SBOM from the **built Docker image** (not only from `requirements.txt`) captures:

- Python packages actually installed in the image
- Debian OS packages from the base image and `apt-get upgrade`
- Transitive/container-only components

This reflects **what ships**, not merely what is declared in source control.

### Why store as a CI artifact?

SBOMs are **point-in-time** records for a specific image build and commit. Storing them as GitHub Actions artifacts (`vulnbank-sbom-cyclonedx`, 30-day retention) avoids committing stale generated files to the repository while preserving evidence for review and audit.

### SBOM is not a vulnerability scanner

The **PR Security Gate — SBOM (Syft)** job validates that inventory generation succeeded and that the CycloneDX document is structurally sound. It does **not** replace:

- **pip-audit** for declared Python dependency CVEs
- **Trivy** for container vulnerability gating

## CI supply-chain flow

```
Source
  ↓
Docker build (vulnbank:sbom)
  ↓
Syft (Anchore SBOM Action)
  ↓
CycloneDX SBOM (sbom.cdx.json)
  ↓
SBOM validation (Python)
  ↓
Artifact retention (30 days)
```

In parallel on the same workflow, **Trivy** independently builds and scans the container image for **fixable HIGH/CRITICAL** vulnerabilities. See [container-security.md](container-security.md) for the Trivy policy.

## Vulnerability policy

Container vulnerability gating remains with **Trivy**:

- **Fixable** HIGH/CRITICAL findings → **block** the PR
- **Vendor-unfixed** HIGH/CRITICAL findings → tracked, documented, do not permanently block (`ignore-unfixed: true`)

The SBOM job does not alter this policy. When Debian publishes fixes, fresh image builds and updated Trivy data reassess previously unfixed findings.

## Limitations

Be accurate about what VulnBank does **not** implement:

- An SBOM describes discovered components; it does **not** prove absence of vulnerabilities
- An SBOM does **not** establish cryptographic provenance or SLSA attestation by itself
- GitHub artifact retention is **finite** (30 days for SBOM artifacts)
- Vulnerability databases and base-image packages change over time
- The generated SBOM represents **that particular image build**, not all historical builds
- SBOM validation checks structure and non-empty inventory, not completeness against every possible component

## Related documentation

- [dependency-management.md](dependency-management.md)
- [container-security.md](container-security.md)
- [README.md — DevSecOps / CI Security](../README.md#devsecops--ci-security)
