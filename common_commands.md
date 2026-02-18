# Common Commands

### Alembic Commands

# Generate a migration from model changes
`alembic revision --autogenerate -m "create initial tables"`

# Apply all pending migrations
`alembic upgrade head`

# Rollback one migration
`alembic downgrade -1`

# See current migration state
`alembic current`

### Testing Commands

# Run all tests (from apps/api/)
`pytest`

# Run with verbose output to see each test name
`pytest -v`

# Run only auth tests
`pytest tests/test_auth_utils.py tests/test_auth_api.py -v`

# Run with coverage report
`pytest --cov=app --cov-report=term-missing`

# Run a single test by name
`pytest -k "test_register_success" -v`