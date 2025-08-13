# Testing Guide for RSS Feed Reader

## Overview

This project uses **pytest** for testing with a comprehensive test suite covering:

- **Unit Tests**: Test individual functions and classes in isolation
- **Integration Tests**: Test how components work together
- **API Tests**: Test HTTP endpoints and authentication
- **Model Tests**: Test database models and relationships

## Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Test configuration and fixtures
├── test_auth.py         # Authentication utilities tests
├── test_models.py       # Database model tests
├── test_processors.py   # Feed/article processing tests
├── test_api.py         # API endpoint tests
└── test_utils.py       # Utility function tests

test_basic.py           # Integration test (existing)
pytest.ini             # Pytest configuration
```

## Running Tests

### Install Test Dependencies

```bash
# Install development dependencies including pytest
make dev
# or
uv sync --extra dev
```

### Run All Tests

```bash
make test
# or
uv run pytest tests/
```

### Run Specific Test Types

```bash
# Unit tests only
make test-unit

# Integration tests
make test-integration

# With coverage report
make test-cov

# Watch mode (re-run on file changes)
make test-watch
```

### Run Specific Test Files

```bash
# Test authentication
uv run pytest tests/test_auth.py

# Test models
uv run pytest tests/test_models.py

# Test specific function
uv run pytest tests/test_auth.py::TestPasswordFunctions::test_password_hashing
```

## Test Coverage

The test suite covers:

### 🔐 Authentication & Security

- Password hashing and verification
- JWT token creation and validation
- User registration and login
- Authentication middleware

### 📊 Database Models

- User model functionality
- RSS feed model and relationships
- Article model and properties
- Model relationships and constraints

### 🔄 Processing Logic

- RSS feed parsing and processing
- Article deduplication
- Content extraction and cleaning
- Error handling in feed processing

### 🌐 API Endpoints

- User registration and authentication
- Feed CRUD operations
- Article retrieval
- Authorization and access control

### 🛠️ Utilities

- Text processing functions
- Configuration management
- Helper functions

## Test Best Practices

### 1. Isolated Tests

- Each test uses a separate in-memory database
- Tests don't depend on external services
- Mocking is used for external dependencies

### 2. Clear Test Names

```python
def test_password_hashing_and_verification():
    """Test that passwords are properly hashed and verified"""
```

### 3. Test Fixtures

```python
@pytest.fixture
def test_db():
    """Provides clean database for each test"""
```

### 4. Async Support

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async functions properly"""
```

## Writing New Tests

### For New Models

1. Add tests to `tests/test_models.py`
2. Test model creation, relationships, properties
3. Test validation and constraints

### For New API Endpoints

1. Add tests to `tests/test_api.py`
2. Test success cases, error cases, authentication
3. Use the `authenticated_client` fixture

### For New Utility Functions

1. Add tests to `tests/test_utils.py`
2. Test edge cases, error handling
3. Test with various input types

### Example Test

```python
def test_create_user_success(test_db):
    """Test successful user creation"""
    user = create_user(
        db=test_db,
        username="testuser",
        email="test@example.com",
        password="secure123"
    )

    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.is_active is True
    assert user.hashed_password != "secure123"  # Should be hashed
```

## CI/CD Integration

Tests are configured to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run Tests
  run: |
    make dev
    make test-cov
```

## Debugging Tests

### Verbose Output

```bash
uv run pytest tests/ -v -s
```

### Debug Specific Test

```bash
uv run pytest tests/test_auth.py::test_user_creation -v -s --tb=long
```

### Coverage Report

```bash
make test-cov
# Opens htmlcov/index.html for detailed coverage
```

## Benefits of This Test Suite

✅ **Catches Bugs Early**: Tests run automatically on code changes
✅ **Documentation**: Tests show how code should be used
✅ **Refactoring Safety**: Confident code changes with test coverage
✅ **API Validation**: Ensures endpoints work correctly
✅ **Multi-User Testing**: Validates user isolation and security
✅ **Performance**: Fast tests with in-memory database
