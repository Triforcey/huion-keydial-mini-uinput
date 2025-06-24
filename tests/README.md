# Testing the Huion Keydial Mini Driver

This directory contains comprehensive tests for the Huion Keydial Mini driver, with a focus on the HID parser functionality.

## Test Structure

- `conftest.py` - Pytest configuration and common fixtures
- `test_hid_parser.py` - Comprehensive tests for the HID parser
- `run_tests.py` - Simple test runner that doesn't require pytest

## Running Tests

### Option 1: Using pytest (Recommended)

```bash
# Install test dependencies
make install-dev

# Run all tests
make test

# Run tests with coverage
make test-cov

# Run specific test file
pytest tests/test_hid_parser.py -v

# Run specific test class
pytest tests/test_hid_parser.py::TestHIDParser -v

# Run specific test method
pytest tests/test_hid_parser.py::TestHIDParser::test_parse_button_press -v
```

### Option 2: Simple tests (No pytest required)

```bash
# Run simple tests without pytest
make test-simple

# Or directly
python3 tests/run_tests.py
```

## Test Coverage

The tests cover:

### HID Parser Tests
- **Button Events**: Press, release, multiple buttons
- **Dial Events**: Clockwise/counterclockwise rotation, clicks
- **Report Formats**: Huion format, standard HID, combined reports
- **Edge Cases**: Empty data, short data, invalid data
- **State Management**: Parser state tracking and reset
- **Configuration**: Different sensitivity settings, missing mappings
- **Error Handling**: Exception handling and graceful degradation

### Test Data
The tests use realistic HID data samples:
- Button reports: `[0x01, button_state, 0x00, ...]`
- Dial reports: `[0x02, dial_delta_low, dial_delta_high, dial_click, ...]`
- Combined reports: `[0x00, buttons_low, buttons_high, dial_delta_low, dial_delta_high, dial_click, ...]`

## Adding New Tests

### For pytest tests:
1. Add test methods to existing classes in `test_hid_parser.py`
2. Use the `@pytest.mark.hid_parser` decorator
3. Use fixtures from `conftest.py` for common setup

### For simple tests:
1. Add test methods to `SimpleHIDParserTest` in `run_tests.py`
2. Follow the unittest pattern with `self.assertEqual()`, etc.

## Test Fixtures

Common fixtures available in `conftest.py`:
- `config` - Sample configuration
- `hid_parser` - HIDParser instance
- `hid_test_data` - Common HID test data
- `mock_logger` - Mocked logger for testing

## Debugging Tests

To debug failing tests:

```bash
# Run with verbose output
pytest tests/ -v -s

# Run with debug logging
pytest tests/ -v -s --log-cli-level=DEBUG

# Run single test with debugger
pytest tests/test_hid_parser.py::TestHIDParser::test_parse_button_press -v -s --pdb
```

## Continuous Integration

The tests are designed to run in CI environments:
- No external dependencies (except pytest for full tests)
- Mocked logging to avoid output pollution
- Isolated test data and fixtures
- Clear error messages and assertions

## Coverage Reports

After running `make test-cov`, you can view detailed coverage reports:
- Terminal output shows coverage summary
- HTML report generated in `htmlcov/` directory
- Open `htmlcov/index.html` in a browser for detailed coverage
