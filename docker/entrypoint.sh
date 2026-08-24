#!/bin/sh
set -e

# Initialise tables if needed (idempotent). Compose waits for PostgreSQL health first.
python init_db.py

exec "$@"
