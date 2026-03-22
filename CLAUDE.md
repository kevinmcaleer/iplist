# CLAUDE.md

## Documentation

- Keep documentation up to date with each new feature or change
- Documentation is in Sphinx format under the `docs/` directory
- Run `make html` from `docs/` to build

## Testing

- Write unit tests for new features and bug fixes
- Use `pytest` for running tests
- Test files should be in the `tests/` directory and named `test_*.py`
- Run `pytest` from the project root to execute all tests
- Aim for high test coverage, especially for critical code paths (80% or higher)
- Use `pytest-cov` to measure test coverage and identify gaps
- Fix any failing tests before merging code changes
- Consider edge cases and error handling in tests
- Use fixtures to set up test data and dependencies
