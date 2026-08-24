# VulnBank

VulnBank is a deliberately vulnerable fintech REST API being developed as an educational Application Security / DevSecOps portfolio project. The goal is to demonstrate secure development practices, vulnerability assessment, and remediation in a realistic API context.

**Current status:** Step 1 — basic Flask application foundation with root and health endpoints. No security features, authentication, or intentional vulnerabilities have been added yet.

## Setup (Windows)

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Run the application

```powershell
python run.py
```

The API will be available at `http://127.0.0.1:5000`.

## Run tests

```powershell
pytest
```

## Endpoints

| Method | Path     | Description              |
|--------|----------|--------------------------|
| GET    | `/`      | API name and online status |
| GET    | `/health`| Health check             |
