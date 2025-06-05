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
print(analyzer.transactions)
# Output transactions from a single statement
#           Date                                        Description  Amount   Balance
# 0   2025-12-31  Card Purchase - Dd/Br.............. .............  -11.81  11940.51
# 1   2025-12-31  Card Purchase - Wendys - ........................  -12.17  11952.32
# 2   2025-12-30  Card Purchase - Walgreens .......................  -4.99  12132.78
# 3   2025-12-30  Recurring Card Purchase 12/30 ...................  -29.25  11964.49
# 4   2025-12-30  Card Purchase - .................................  -31.56  11993.74
# ..         ...                                                ...     ...       ...
# 272 2025-01-02  Card Purchase - Dd *Doordash Wingsto Www.Doord...  -10.16  11930.35
# 273 2025-01-02  Card Purchase - Walgreens .................. ...   -4.43  11925.92
# 274 2025-01-02  Card Purchase - Kings ...........................  -40.28  11859.62
# 275 2025-01-02  Card Purchase - Tst* ...........................   -7.02  11918.90
# 276 2025-01-02  Zelle Payment To ................................  -19.00  11899.90



# Output checking summary for a single statement
print(analyzer.checking_summary)
# Output:
#                        Category    Amount
# 0             Beginning Balance  11679.61
# 1        Deposits and Additions   2955.39
# 2  ATM & Debit Card Withdrawals  -1024.11
# 3        Electronic Withdrawals   -134.62
# 4                Ending Balance  13476.27
# 5             Total Withdrawals   1158.73
# 6                   Net Savings   1796.66
# 7                 % Saving Rate     60.79






# Directory analysis
analyzer = CBSAnalyzer("path/to/statements/")
all_data = analyzer.all_transactions
print(all_data)
# Output all transactions from multiple statements
#            Date                                        Description  Amount   Balance
# 0    2025-12-31  Card Purchase - Dd/Br.............. .............  -12.17  11952.32
# 1    2025-12-31  Card Purchase - Wendys - ........................  -11.81  11940.51
# 2    2025-12-30  Card Purchase - Walgreens .......................  -57.20  12066.25
# 3    2025-12-30  Recurring Card Purchase 12/30 ...................  -31.56  11993.74
# 4    2025-12-30  Card Purchase - .................................  -20.80  12025.30
# ...         ...                                                ...     ...       ...
# 1769 2023-01-03  Card Purchase - Dd *Doordash Wingsto Www.Doord..   -4.00   1837.81
# 1770 2023-01-03  Card Purchase - Walgreens .................. ...   100.00   1765.72
# 1771 2023-01-03  Card Purchase - Kings ..........................   -3.91   1841.81
# 1772 2023-01-03  Card Purchase - Tst* ..........................    70.00   1835.72
# 1773 2023-01-03  Zelle Payment To ...............................   10.00   1845.72


# ----------------------------------------------------


# Output all checking summaries from multiple statements
analyzer = CBSAnalyzer("path/to/statements/")
all_data = analyzer.all_checking_summaries
print(all_data)
#       Date  Beginning Balance  Deposits and Additions  ATM & Debit Card Withdrawals  Electronic Withdrawals  Ending Balance  Total Withdrawals  Net Savings  % Saving Rate
# 0  2025-04           14767.33                 2535.82                      -1183.41                 -513.76        15605.98            1697.17       838.65          33.07
# 1  2025-03           14319.87                 4319.20                      -3620.85                 -250.89        14767.33            3871.74       447.46          10.36
# 2  2025-02           13476.27                 2328.18                       -682.24                 -802.34        14319.87            1484.58       843.60          36.23
# 3  2025-01           11679.61                 2955.39                      -1024.11                 -134.62        13476.27            1158.73      1796.66          60.79
```


# ----------------------------------------------------



### Advanced Analysis
```python
# Monthly spending analysis
monthly_spending = analyzer.analyze_transactions(
    by_month=True,
    column="Transactions_Count"
)

# Output:
#       Month  Maximum
# 0  February      205




# Annual savings rate
annual_savings = analyzer.analyze_summaries(
    by_year=True,
    column="% Saving Rate_Mean"
)

# Output:
#      Year  Maximum
# 0  2024.0    36.01
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