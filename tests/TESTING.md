# Testing Guide for WAVE Project

## Quick Start

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_metadata.py -v

# Run with coverage
pytest --cov=src --cov-report=html
```

## Test Files Created

- ✅ `tests/conftest.py` — Shared fixtures for all tests
- ✅ `tests/test_metadata.py` — Configuration and metadata tests
- ✅ `tests/test_reporting.py` — Logging and reporting tests
- ✅ `tests/test_data_extraction.py` — CSV/Excel extraction tests
- ✅ `tests/test_data_formatter.py` — Data formatting and transformation tests
- ✅ `tests/test_data_comparator.py` — DataFrame comparison tests
- ✅ `tests/test_data_appender.py` — Data upsert/append tests

## What's Tested

| Module             | Coverage                                              | Key Tests |
| ------------------ | ----------------------------------------------------- | --------- |
| metadata.py        | TableType enum, AppMetadata methods                   | 15+ tests |
| reporting.py       | Log methods, file persistence, formatting             | 20+ tests |
| data_extraction.py | CSV reading, NA handling, error recovery              | 10+ tests |
| data_formatter.py  | Whitespace normalization, filtering, column alignment | 20+ tests |
| data_comparator.py | Shape comparison, row differences                     | 10+ tests |
| data_appender.py   | Upsert logic, CSV export                              | 10+ tests |

**Total: 85+ unit tests**

## Running Tests

### All Tests

```bash
pytest
```

### With Verbose Output

```bash
pytest -v
```

### Specific File

```bash
pytest tests/test_metadata.py -v
```

### Specific Class

```bash
pytest tests/test_metadata.py::TestTableType -v
```

### Specific Test

```bash
pytest tests/test_metadata.py::TestTableType::test_table_type_values -v
```

### By Keyword

```bash
pytest -k "filter" -v
```

### With Coverage

```bash
pytest --cov=src --cov-report=html
# Then open htmlcov/index.html
```

## Test Organization

### Fixtures (conftest.py)

Reusable setup for all tests:

```python
@pytest.fixture
def mock_window():
    """Mock Tkinter window"""

@pytest.fixture
def temp_report_dir():
    """Temporary directory for reports"""

@pytest.fixture
def reporting(mock_window, temp_report_dir):
    """Pre-configured Reporting instance"""

@pytest.fixture
def mock_app_metadata():
    """Mock AppMetadata instance"""

@pytest.fixture
def sample_dataframe():
    """Sample 3-row DataFrame"""
```

### Test Patterns

**Testing Return Values:**

```python
def test_could_extract_both_valid(self, reporting, mock_app_metadata, sample_dataframe):
    extractor = DataExtractor(reporting, mock_app_metadata)
    result = extractor.could_extract(sample_dataframe, sample_dataframe)
    assert result is True
```

**Testing Exceptions:**

```python
def test_invalid_worksheet_raises_error(self):
    with pytest.raises(KeyError):
        AppMetadata("INVALID_WORKSHEET")
```

**Testing Data Transformation:**

```python
def test_upsert_appends_new_rows(self, reporting, mock_app_metadata):
    appender = DataAppender(reporting, mock_app_metadata)
    result = appender.upsert(mtl_df, input_df)
    assert len(result) == 4  # 2 + 2 new rows
```

**Testing File Operations:**

```python
def test_save_report_creates_file(self, reporting):
    reporting.info("Test message")
    reporting.save_report()
    assert reporting.file_path.exists()
```

## Key Test Classes

### TestTableType

- Enum values correct
- Casting from int works
- Invalid values raise ValueError

### TestReportingInitialization

- Report creation with parameters
- Default values set correctly
- Custom timestamps accepted

### TestDataFormatterFilterByString

- Exact match filtering
- Wildcard patterns (\* prefix, suffix, both)
- No matches return empty
- Empty string returns original

### TestDataFormatterFormat

- Converts to string type
- Removes blank columns
- Drops empty rows on index keys
- Returns empty on None

### TestDataAppenderUpsert

- Appends new rows
- Updates existing rows (true upsert)
- Preserves column order
- Handles empty inputs

### TestDataComparatorShapes

- Detects equal shapes
- Finds row differences
- Finds column differences
- Returns empty dict on empty df

## Understanding Output

### Success

```
tests/test_metadata.py::TestTableType::test_table_type_values PASSED
```

### Failure

```
tests/test_metadata.py::TestTableType::test_invalid_table_type_raises_error FAILED
AssertionError: Expected ValueError, but no exception was raised
```

### Summary

```
======================== 85 passed in 2.34s ==========================
```

## Best Practices

### 1. Before Committing

```bash
pytest && git commit -m "feature: new feature"
```

### 2. Check Coverage

```bash
pytest --cov=src --cov-report=term-missing
```

Target: >80% on core modules

### 3. Descriptive Names

```python
# ❌ Bad
def test_format(self):

# ✅ Good
def test_format_converts_numeric_columns_to_string(self):
```

### 4. Independent Tests

Each test runs standalone, uses fixtures:

```python
def test_verify_saved_report(self, reporting):
    reporting.info("Test")
    reporting.save_report()
    assert reporting.file_path.exists()
```

### 5. Regression Tests

When fixing bugs, add a test:

```python
def test_filter_handles_special_characters(self, reporting, mock_app_metadata):
    """Regression: filter should handle * in data"""
    formatter = DataFormatter(reporting, mock_app_metadata)
    df = pd.DataFrame({"Name": ["Item*Special"]})
    result = formatter.filter_by_string(df, "Item*Special")
    assert len(result) == 1
```

## Troubleshooting

### ModuleNotFoundError: No module named 'src'

```bash
touch src/__init__.py
pytest
```

### Fixture Not Found

- Check spelling in conftest.py
- Ensure conftest.py is in tests/ folder

### File Permission Errors

- Close files in Excel
- Run with admin privileges if needed

## Next Steps

1. Run tests: `pytest -v`
2. Check coverage: `pytest --cov=src`
3. Add tests for new features
4. Fix failures based on assertion errors
5. Commit passing tests

## Documentation

- Pytest: https://docs.pytest.org/
- Fixtures: https://docs.pytest.org/en/stable/fixture.html
- Parametrize: https://docs.pytest.org/en/stable/parametrize.html
- Coverage: https://coverage.readthedocs.io/
