# Dependency Management

## Why it matters

VulnBank depends on third-party Python packages (Flask, SQLAlchemy, PyJWT, etc.). Vulnerabilities in those dependencies can affect the application even when application code is secure. Dependency management is part of defence-in-depth for this project.

## Project dependencies

Runtime application dependencies are declared in [`requirements.txt`](../requirements.txt). Development and CI security tooling (`bandit`, `pip-audit`, `pytest`) are in [`requirements-dev.txt`](../requirements-dev.txt), which is **not** installed in the Docker image.

Install for local development and security checks:

```powershell
pip install -r requirements-dev.txt
```

The Docker image installs only `requirements.txt`.

## Automated scanning (CI)

The GitHub Actions **Security Pipeline** (`.github/workflows/security.yml`) runs **pip-audit** on every push to `vulnerable-lab` and on pull requests targeting that branch.

The **PR Security Gate - SCA (pip-audit)** job:

- Installs dependencies from `requirements.txt`
- Runs `pip-audit -r requirements.txt`
- **Fails the workflow** if known vulnerabilities are found in declared dependencies

This prevents merging changes that introduce vulnerable package versions.

## Local dependency audit

Run the same check locally before opening a pull request:

```powershell
pip install -r requirements-dev.txt
pip-audit -r requirements.txt
```

Use `-r requirements.txt` to audit **project dependencies only**, not every package installed in your virtual environment (e.g. the `pip` tool itself).

## When vulnerabilities are found

1. **Identify** - note the package name, installed version, and advisory ID from pip-audit output
2. **Investigate** - read the advisory; determine whether VulnBank code paths are affected
3. **Upgrade** - where a fixed version exists, update the minimum version in `requirements.txt`
4. **Verify** - run `pytest -v` and `pip-audit -r requirements.txt` again
5. **Document** - significant dependency fixes may be noted in commit messages or security documentation as appropriate

Do not suppress pip-audit findings in CI merely to make the pipeline pass. Prefer upgrading or replacing affected dependencies.

## Related documentation

- [SECURITY.md](../SECURITY.md) - vulnerability reporting policy
- [README.md - DevSecOps / CI Security](../README.md#devsecops--ci-security) - full pipeline overview
- [security/README.md](README.md) - security lifecycle index
