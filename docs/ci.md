# CI / CD

## GitHub Actions Workflow

The repository includes a CI workflow at `.github/workflows/ci.yml` that runs
on every push and pull request to `master`/`main`.

### What it runs

1. **Unit tests** — `pytest services/stage1/tests/ -v`
2. **Smoke regression** — `python scripts/run_regression.py --suite smoke --strict`

### Requirements

- Python 3.12
- All dependencies from `requirements.txt`
- Golden files in `test-data/golden/`
- Output fixtures in `output/`

### Local verification

Run the same checks locally before pushing:

```bash
# Unit tests
python -m pytest services/stage1/tests/ -v

# Regression
python scripts/run_regression.py --suite smoke --strict
```

### Extending

To add more test suites:

1. Add test files under the appropriate `tests/` directory
2. Update the workflow steps if new test directories are added
3. For integration tests that require Azure credentials, use a separate
   workflow with `workflow_dispatch` and secrets configured
