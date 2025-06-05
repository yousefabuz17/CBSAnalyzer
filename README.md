# CBS Analyzer
[![PyPI version](https://badge.fury.io/py/cbs-analyzer.svg)](https://badge.fury.io/py/cbs-analyzer)
[![Downloads](https://static.pepy.tech/badge/cbs-analyzer)](https://pepy.tech/project/cbs-analyzer)
[![License](https://img.shields.io/badge/license-Apache-blue.svg)](https://opensource.org/license/apache-2-0/)
[![Documentation](https://img.shields.io/badge/docs-latest-brightgreen.svg)](https://github.com/yourorg/cbs-analyzer/blob/main/README.md)
[![Code Style](https://img.shields.io/badge/code%20style-pep8-blue.svg)](https://www.python.org/dev/peps/pep-0008/)

# CBS Analyzer

`CBS Analyzer` is a financial analysis tool designed to process and analyze Chase Bank PDF statements. This project transforms raw bank statements into structured, analyzable data with powerful aggregation and export capabilities.

## Table of Contents
- [Installation](#installation)
- [Features](#features)
- [Parameters](#parameters)
- [Attributes](#attributes)
- [Methods](#methods)
- [Usage Examples](#usage-examples)
- [Error Handling](#error-handling)
- [Contributing](#contributing)
- [License](#license)

---

## Installation

```bash
pip install cbs-analyzer
```

---

## Features

- **Multi-Statement Processing**: Analyze single statements or entire directories
- **Comprehensive Financial Metrics**:
  - Monthly/Yearly spending trends
  - Cash flow analysis
  - Savings rate calculations
- **Flexible Data Export**: CSV, Excel, JSON, and Parquet formats
- **Advanced Analysis**:
  - Time-based aggregation (day/month/year)
  - Statistical summaries
  - Custom column analysis
- **Enterprise-Grade Infrastructure**:
  - Thread-safe processing
  - Cached properties for performance
  - Comprehensive error handling

---

## Parameters

### Core Parameters
- `file_path` (`PathLike`): Path to PDF file or directory
- `ascending_date` (`bool`): Sort transactions chronologically (default: False)

### Analysis Parameters
- `by_year`/`by_month`/`by_day` (`bool`): Time-based grouping
- `column` (`str`): Specific column to analyze
- `minimum` (`bool`): Find minimum values instead of maximum

---

## Attributes

- `transactions`: Single statement transactions (DataFrame)
- `checking_summary`: Single statement summary (DataFrame)
- `all_transactions`: All statements' transactions (DataFrame)
- `all_checking_summaries`: All statements' summaries (DataFrame)

---

## Methods

### Core Methods
- `analyze_summaries()`: Analyze checking account summaries
- `analyze_transactions()`: Analyze transaction data
- `export()`: Export data to various formats

---

## Usage Examples

### Basic Analysis
```python
from cbs_analyzer import CBSAnalyzer

# Single statement analysis
analyzer = CBSAnalyzer("path/to/statement.pdf")
print(analyzer.transactions.head())
print(analyzer.checking_summary)

# Directory analysis
analyzer = CBSAnalyzer("path/to/statements/")
all_data = analyzer.all_transactions
```

### Advanced Analysis
```python
# Monthly spending analysis
monthly_spending = analyzer.analyze_transactions(
    by_month=True,
    column="Amount"
)

# Annual savings rate
annual_savings = analyzer.analyze_summaries(
    by_year=True,
    column="% Saving Rate"
)
```

### Data Export
```python
# Export to different formats
analyzer.all_transactions.export("transactions.xlsx")
analyzer.checking_summary.export("summary.json")
analyzer.checking_summary.export(".json")
analyzer.checking_summary.export("csv")
```

#### Various cases for export_path:
1. Export path is empty ("")
   export_path="" -> "cbsanalyzer.csv"
2. Export path is a directory
   export_path="path/to/dir/" -> "path/to/dir/cbsanalyzer.csv"
3. Export path is a file name only
   export_path="file" -> "file.csv"
4. Export path is an extension type
   export_path=".csv" | "csv" -> "cbsanalyzer.csv"
5. Export path is a file with a given extension
   export_path="file.csv" -> "file.csv"
6. Export path is a hidden file name
   export_path="</dir/>.hidden.csv" -> "</dir/>.hidden.csv"
7. Export path is the current (".") or home directory ("~")
   export_path="." -> "</cwdir/>/cbsanalyzer.csv"
   export_path="~" -> "</home/>/cbsanalyzer.csv"
```

---

## Error Handling

The analyzer provides detailed error messages for:
- File access issues
- Malformed PDF content
- Invalid analysis parameters

Example error handling:
```python
try:
    analyzer = CBSAnalyzer("invalid_path.pdf")
except FileNotFoundError as e:
    print(f"Error loading statement: {e}")
```


---


## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a Pull Request

### Development Setup
```bash
pip install -e ".[dev]"
pytest tests/
```

---

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

---

**CBS Analyzer** © 2025  
Chase is a registered trademark of JPMorgan Chase & Co.  
Not affiliated with or endorsed by JPMorgan Chase & Co.