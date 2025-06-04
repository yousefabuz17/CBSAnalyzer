import pandas as pd
import re
import subprocess

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime as dt
from functools import (
    cache,
    cached_property,
    partial
)
from pathlib import Path
from typing import (
    Callable,
    Iterable,
)

from .exceptions import (
    CBSException,
    FileException,
)
from .type_hints import (
    DataFrameLike,
    DictOrDataFrameLike,
    FormatTypes,
    IndexLike,
    IterablePathLike,
    NestedStringTuples,
    OptionalFormatTypes,
    PathLike,
    StringTuple,
)
from .utils import (
    check_fp,
    clean_float,
    clean_path,
    extract_statement_date,
    popkwargs,
    universal_date
)
from .wrappers import (
    ClassProperty,
    WRAPPERS
)



# region FileHandler
class FileHandler:
    UTILS_DIR: Path = Path(__file__).absolute().resolve()
    FILE_HANDLER_SH: Path = (UTILS_DIR.parent / "file_handler.sh").absolute()
    
    _PIPE: int = subprocess.PIPE
    _SEPERATOR: str = "^^"
    _FILE_HANDLER_FUNCTIONS: dict = {
        "getFiles": "--get-files",
        "grepFiles": "--grep-files",
        "checkingSummary": "--checking-summary"
    }
    
    __dict__ = {}
    __slots__ = (
        "__weakrefs__",
        "_fp",
        "_is_file",
        "_bank_statements"
        )
    
    def __init__(self, file_path: PathLike) -> None:
        self._fp = check_fp(file_path, is_file=False)
        self._is_file = check_fp(self._fp, check_is_file=True)
        self._bank_statements = None
    
    @classmethod
    def _process_cmd(
        cls,
        cmd: list, 
        cinput: str = None, 
        unpack: bool = True, 
        strip: bool = True
        ):
        script = subprocess.Popen(
            cmd,
            stdin=cls._PIPE,
            stdout=cls._PIPE,
            stderr=cls._PIPE,
            text=True
            )
        
        if not unpack:
            return script
        
        stdout, stderr = script.communicate(input=cinput)
        return (
            stdout.strip() if strip else stdout,
            stderr,
            script.returncode
        )
    
    @classmethod
    @cache
    def source_handler(cls, *args, **kwargs) -> IterablePathLike:
        if not cls.FILE_HANDLER_SH.is_file():
            raise FileException(
                f"File handler script not found. Please make sure the ({cls.FILE_HANDLER_SH!r}) script is in the correct directory."
            )
        functions = (*cls._FILE_HANDLER_FUNCTIONS.keys(),)
        bash_cmd, func, kwargs = popkwargs("cmd", "func", **kwargs)
        script_func = cls._FILE_HANDLER_FUNCTIONS.get(func)
        
        if all((bash_cmd, func)):
            raise FileException(
                "Please provide either a bash command or a function name, not both."
                "\nIf you want to use a function, please provide a valid function name from the following:"
                f"\n{functions = }"
                f"\nProvided bash command: {bash_cmd = }"
                f"\nProvided function name: {func = }"
            )
        
        if not script_func:
            raise FileException(
                "Invalid function name provided. Please provide a valid function name from the following:"
                f"\n{functions}"
            )
        
        if not bash_cmd and script_func:
            bash_cmd = f'''
            source "{cls.FILE_HANDLER_SH}" \
            && getFunction {script_func} {" ".join(args)} \
            '''
        script_stdout, script_stderr, return_code = cls._process_cmd(cmd=["bash", "-c", bash_cmd])

        if return_code != 0:
            raise FileException(
                f"File handler script ({cls.FILE_HANDLER_SH!r}) failed to execute. Please check the script and try again."
                f"\nReturn Error: {script_stderr!r}"
            )
        
        if not script_stdout:
            raise FileException(
                f"File handler script ({cls.FILE_HANDLER_SH!r}) returned an empty output. Please check the script and try again."
            )
        return script_stdout
    
    def _get_bank_statements(self) -> IterablePathLike:
        bank_statements = self.source_handler(f'-f "{self._fp}"', func="getFiles")
        valid_files = ()
        for statement in bank_statements.split(self._SEPERATOR):
            clean_statement = clean_path(statement)
            if check_fp(clean_statement, check_is_file=True):
                valid_files += (Path(clean_statement),)

        if not valid_files:
            raise FileException(
                f"No valid PDF files were found in the specified directory ({self._fp!r})."
                "\nPlease make sure the directory contains valid PDF files."
                "\nIf the issue persists, please check the file handler script."
            )
        return valid_files
    
    @cached_property
    @WRAPPERS["PropertyDirOnly"]
    def bank_statements(self) -> IterablePathLike:
        """
        Returns a cached tuple of all the Chase Bank Statement PDF files in the specified directory.
        """
        if self._bank_statements is None:
            self._bank_statements = self._get_bank_statements()
        return self._bank_statements



# region CoreHandler
class CoreHandler(FileHandler):
    FORMAT_TYPES: FormatTypes = ("dataframe", "dict", "")
    TRANSACTION_COLUMNS: StringTuple = \
        (
        "Date",
        "Description",
        "Amount",
        "Balance"
        )
    CHECKING_SUMMARY_COLUMNS: NestedStringTuples = \
        {
        "Outer": ("Category", "Amount"),
        "Inner": (
            "Date",
            "Beginning Balance",
            "Deposits and Additions",
            "ATM & Debit Card Withdrawals",
            "Electronic Withdrawals",
            "Ending Balance",
            "Total Withdrawals",
            "Net Savings",
            "% Saving Rate"
        )
    }
    
    __dict__ = {}
    __slots__ = (
        "__weakrefs__",
        "_checking_summary",
        "_transactions"
        )
    
    def __init__(
        self,
        file_path: PathLike = None,
        ) -> None:
        super().__init__(file_path=file_path)
        
        self._checking_summary = None
        self._transactions = None
    
    @classmethod
    def _validate_type(
        cls,
        __type: OptionalFormatTypes,
        types: Iterable = None,
        type_category: str = "format"
        ) -> str:
        types = types or cls.FORMAT_TYPES
        l_type = __type.lower()
        if l_type not in types:
            raise CBSException(
                f"Invalid {type_category} type {__type!r}."
                f"\nExpected {types = }"
            )
        return l_type
    
    @classmethod
    def convert_data(cls, data: DictOrDataFrameLike, format_type: OptionalFormatTypes = ""):
        if not isinstance(data, (list, dict, DataFrameLike)):
            raise CBSException(
                f"Invalid data type {type(data).__name__!r}. "
                f"Expected a {list[dict]!r}, {DictOrDataFrameLike.__name__!r} object."
            )
        
        format_type = cls._validate_type(format_type)
        df_data = data
        match format_type:
            case "dict":
                if isinstance(data, DataFrameLike):
                    df_data = data.to_dict()
            case "dataframe"|"":
                if isinstance(data, (list, dict)):
                    df_data = cls.create_dataframe(data)
                elif isinstance(data, DataFrameLike):
                    df_data = df_data.reset_index(drop=True)
        return df_data
    
    @ClassProperty
    def core_handler(cls):
        return cls
    
    @staticmethod
    def create_dataframe(
        data,
        index_reset: bool = False,
        index: IndexLike = None,
        index_name = ""
        ) -> DataFrameLike:
        if index_reset:
            return pd.DataFrame(data, index=[0])
        
        dataframe = pd.DataFrame(data)
        
        if all((index_reset, index)):
            raise CBSException(
                "Cannot reset index and set index at the same time. "
                "Please set either `reset_index` or `index`, not both."
            )
        
        index_func = partial(pd.Index, name=index_name)
        if index and not index_reset:
            dataframe.index = index_func(index)
        else:
            dataframe = dataframe.reset_index(drop=True)
        return dataframe
    
    @staticmethod
    def _concat(data: Iterable[DataFrameLike], **kwargs):
        try:
            return pd.concat(data, **kwargs)
        except Exception as e:
            raise FileException(
                "An error occurred while concatenating the data. "
                "Please ensure all pdf bank statement files are in the correct format."
            ) from e
    
    def _get_checking_summary(self) -> DictOrDataFrameLike:
        c_summary_args = f'-f "{self._fp}"'
        c_summary_func = partial(self.source_handler, func="checkingSummary")
        
        # Checking-Summary Keys
        c_summary_keys = c_summary_func(f'{c_summary_args} -k').split("\n")
        
        # Checking-Summary Values
        c_summary = c_summary_func(f'{c_summary_args}')
        awk_script = """
        BEGIN { FS=": "; OFS="," }
        { print $2 }
        """
        c_summary_script, stderr, returncode = self._process_cmd(cmd=["awk", awk_script], cinput=c_summary)
        if returncode != 0:
            raise CBSException(
                "Failed to execute the checking summary script. "
                "Please check the file handler script and ensure it is executable.",
                f"Return Error: {stderr!r}"
            )
        
        try:
            c_summary_values =(*map(clean_float, c_summary_script.split("\n")),)
        except ValueError as ve:
            raise CBSException(
                "Failed to parse the checking summary values. "
                "Please ensure the file handler script is working correctly.",
                ) from ve
        
        if not c_summary_values:
            raise CBSException(
                "The checking summary is empty. "
                "Please ensure the bank statement is the correct format and the file handler script is working correctly."
                )
        
        default_columns = self.CHECKING_SUMMARY_COLUMNS["Outer"]
        full_csummary = dict(
            zip(
                default_columns,
                (c_summary_keys, c_summary_values)
                )
            )
        full_csummary_df = self.convert_data(full_csummary, format_type="dataframe")
        get_value = lambda k: full_csummary_df.loc[full_csummary_df["Category"] == k, "Amount"].values[0]
        beginning_balance, ending_balance = (*(map(get_value, ("Beginning Balance", "Ending Balance"))),)
        net_savings = ending_balance - beginning_balance
        atm_debit_withdrawls, electronic_withdrawls = (*(map(get_value, ("ATM & Debit Card Withdrawals", "Electronic Withdrawals"))),)
        total_withdrawals = abs(electronic_withdrawls + atm_debit_withdrawls)
        deposits_additions = get_value("Deposits and Additions")
        savings_rate = round((net_savings / deposits_additions) * 100, 2)
        new_df = self.create_dataframe(dict(
            zip(
                default_columns,
                (
                    ("Total Withdrawals", "Net Savings", "% Saving Rate"),
                    (total_withdrawals, net_savings, savings_rate)
                )
            )
        ))
        full_csummary_df = self._concat([full_csummary_df, new_df])
        return self.convert_data(full_csummary_df)
    
    def _get_transactions(self):
        def fix_descr(description: str):
            return re.sub(
                r"^Card Purchase\s+(.*?)(\d{2}/\d{2})",
                "Card Purchase -",
                description.strip()
                )
        
        statement_transactions = self.source_handler(f'-f "{self._fp}"', func="grepFiles")
        date_year = extract_statement_date(self._fp, year_only=True)
        txn_data = []
        for line in statement_transactions.splitlines():
            # Match pattern:
            # DATE mm/dd ... DESCRIPTION ... AMOUNT ... BALANCE
            match = re.match(
                r'^(\d{2}/\d{2})\s+(.*?)(-?\d[\d,.]*)\s+([\d,]+\.\d{2})$',
                line.strip()
                )
            if match:
                date, desc, amount, balance = match.groups()
                full_date = f"{date}/{date_year}"
                fixed_date = dt.strptime(full_date, "%m/%d/%Y")
                values = (
                            universal_date(fixed_date),
                            fix_descr(desc),
                            *map(clean_float, (amount, balance)),
                        )
                txn_data.append(dict(zip(self.TRANSACTION_COLUMNS, values)))
        
        if not txn_data:
            raise CBSException(
                f"No transactions were found in the statement ({self._fp!r}). "
                "If not expected, please check the file handler script and ensure it is working correctly.",
            )
        
        return self.convert_data(txn_data)
    
    @cached_property
    def get_checking_summary(self) -> DictOrDataFrameLike:
        if self._checking_summary is None:
            self._checking_summary = self._get_checking_summary()
        return self._checking_summary
    
    @cached_property
    def get_transactions(self) -> DictOrDataFrameLike:
        if self._transactions is None:
            self._transactions = self._get_transactions()
        return self._transactions



# region DirHandler
class CoreDirHandler:
    CORE_HANDLER = CoreHandler
    
    __dict__ = {}
    __slots__ = (
        "__weakrefs__",
        "_statements",
        "_all_checking_summaries",
        "_all_transactions",
        )
    
    def __init__(
        self,
        statements: IterablePathLike,
        ) -> None:
        self._statements = self._validate_statements(statements)
        self._all_checking_summaries = None
        self._all_transactions = None
    
    def map(self, fn: Callable, *iterables, timeout=None, chunksize=1):
        yield from ThreadPoolExecutor().map(fn, *iterables, timeout=timeout, chunksize=chunksize)
    
    def _validate_statements(self, statements: IterablePathLike):
        if not isinstance(statements, Iterable):
            raise CBSException(
                "`statements` must be an iterable of file paths. "
                f"Received {statements!r} of type {type(statements).__name__!r}."
            )
        
        if len(statements) == 0:
            raise CBSException(
                "No statements were provided. "
                "Please provide at least one statement file path."
            )
        yield from (*self.map(check_fp, statements),)
    
    @classmethod
    def convert_data(cls, *args, **kwargs) -> DictOrDataFrameLike:
        return cls.CORE_HANDLER.convert_data(*args, **kwargs)
    
    @classmethod
    def _change_dates(cls, dataframe: DataFrameLike, date_format: str = ""):
        dt_format = date_format or "M"
        dataframe['Date'] = dataframe['Date'].dt.to_period(dt_format)
        return dataframe
    
    def _map_statements(self, func: Callable):
        yield from self.map(func, self._statements)

    def _get_all_summaries(self) -> DataFrameLike:
        def map_summaries(statement):
            statement_csummary = self.CORE_HANDLER(statement)._get_checking_summary()
            get_column_values = lambda k: statement_csummary.loc[:, k].values
            
            columns, column_values = map(get_column_values, ("Category", "Amount"))
            df_data = {
                "Date": [extract_statement_date(statement)],
                **{k: v for k,v in zip(columns, column_values)}
            }
            return self.CORE_HANDLER.create_dataframe(df_data)
        
        all_summaries = self._map_statements(map_summaries)
        all_summaries_df = self.CORE_HANDLER._concat(all_summaries, ignore_index=True)
        return self._change_dates(all_summaries_df).round(2)
    
    def _get_all_transactions(self) -> DataFrameLike:
        map_transactions = lambda t: self.CORE_HANDLER(t)._get_transactions()
        all_transactions = self._map_statements(map_transactions)
        return self.CORE_HANDLER._concat(all_transactions).round(2)
    
    @cached_property
    def get_all_checking_summaries(self) -> DictOrDataFrameLike:
        if self._all_checking_summaries is None:
            self._all_checking_summaries = self._get_all_summaries()
        return self._all_checking_summaries
    
    @cached_property
    def get_all_transactions(self) -> DictOrDataFrameLike:
        if self._all_transactions is None:
            self._all_transactions = self._get_all_transactions()
        return self._all_transactions



# region CBSMainCore
class CBSMainCore(CoreHandler):
    DIR_HANDLER = CoreDirHandler
    CORE_EXECUTOR = DIR_HANDLER.__base__ # CoreExecutor
    
    __dict__ = {}
    __slots__ = (
        "__weakrefs__",
        "_ascending_date",
        )
    
    def __init__(
        self,
        file_path: PathLike,
        *,
        ascending_date: bool = False,
        ) -> None:
        super().__init__(
            file_path=file_path,
            )
        self._ascending_date = ascending_date
    
    @ClassProperty
    @WRAPPERS["Columns"]
    @cache
    def checking_summary_columns(cls) -> NestedStringTuples:
        """
        Returns the columns for the checking summary DataFrame.
        The columns are structured as a dictionary with two keys:
        - "Outer": Contains the main categories of the checking summary.
        - "Inner": Contains the detailed columns for each category.
        
        Example:
        >>> CBSMainCore.checking_summary_columns
        {
            "Outer": ("Category", "Amount"),
            "Inner": (
                "Date",
                "Beginning Balance",
                "Deposits and Additions",
                "ATM & Debit Card Withdrawals",
                "Electronic Withdrawals",
                "Ending Balance",
                "Total Withdrawals",
                "Net Savings",
                "% Saving Rate"
            )
        }
        """
        pass
    
    @ClassProperty
    @WRAPPERS["Columns"]
    @cache
    def transaction_columns(cls) -> StringTuple:
        """
        Returns the columns for the transactions DataFrame.
        The columns are:
        - "Date": The date of the transaction.
        - "Description": The description of the transaction.
        - "Amount": The amount of the transaction.
        - "Balance": The balance after the transaction.
        
        Example:
        >>> CBSMainCore.transaction_columns
        ("Date", "Description", "Amount", "Balance")
        """
        pass
    
    @cached_property
    @WRAPPERS["PropertyFilesOnly"]
    @WRAPPERS["PropertyCore"]
    def checking_summary(self) -> DictOrDataFrameLike:
        """
        Returns the checking summary for the bank statement file.
        
        The checking summary includes the following columns:
        - "Category": The category of the checking summary.
        - "Amount": The amount for each category.
        
        The summary is structured as a DataFrame with the following columns:
        - "Date": The date of the statement.
        - "Beginning Balance": The starting balance for the statement period.
        - "Deposits and Additions": The total deposits and additions for the statement period.
        - "ATM & Debit Card Withdrawals": The total ATM and debit card withdrawals for the statement period.
        - "Electronic Withdrawals": The total electronic withdrawals for the statement period.
        - "Ending Balance": The ending balance for the statement period.
        - "Total Withdrawals": The total withdrawals for the statement period.
        - "Net Savings": The net savings for the statement period.
        - "% Saving Rate": The saving rate for the statement period.
        
        Example:
        >>> cbs_core = CBSMainCore(file_path="path/to/bank_statement.pdf")
        >>> checking_summary = cbs_core.checking_summary
        >>> print(checking_summary)
        {
            "Category": ["Beginning Balance", "Deposits and Additions", ...],
            "Amount": [1000.00, 500.00, ...],
            "Date": ["2023-01-01", ...],
            "Beginning Balance": [1000.00, ...],
            "Deposits and Additions": [500.00, ...],
            "ATM & Debit Card Withdrawals": [200.00, ...],
            "Electronic Withdrawals": [100.00, ...],
            "Ending Balance": [1200.00, ...],
            "Total Withdrawals": [300.00, ...],
            "Net Savings": [200.00, ...],
            "% Saving Rate": [20.00, ...]
        }
        """
        pass
    
    @cached_property
    @WRAPPERS["PropertyFilesOnly"]
    @WRAPPERS["SortDate"]
    @WRAPPERS["PropertyCore"]
    def transactions(self) -> DictOrDataFrameLike:
        """
        Returns the transactions for the bank statement file.
        
        The transactions include the following columns:
        - "Date": The date of the transaction.
        - "Description": The description of the transaction.
        - "Amount": The amount of the transaction.
        - "Balance": The balance after the transaction.
        
        The transactions are structured as a DataFrame with the following columns:
        - "Date": The date of the transaction.
        - "Description": The description of the transaction.
        - "Amount": The amount of the transaction.
        - "Balance": The balance after the transaction.
        
        Example:
        >>> cbs_core = CBSMainCore(file_path="path/to/bank_statement.pdf")
        >>> transactions = cbs_core.transactions
        >>> print(transactions)
        {
            "Date": ["2023-01-01", "2023-01-02", ...],
            "Description": ["Purchase at Store A", "Deposit at ATM B", ...],
            "Amount": [-50.00, 100.00, ...],
            "Balance": [950.00, 1050.00, ...]
        }
        """
        pass
    
    @cached_property
    @WRAPPERS["PropertyDirOnly"]
    @WRAPPERS["SortDate"]
    @WRAPPERS["PropertyDir"]
    def all_checking_summaries(self) -> DictOrDataFrameLike:
        """
        Returns all checking summaries for the bank statements in the directory.
        
        The summaries are structured as a DataFrame with the following columns:
        - "Date": The date of the statement.
        - "Category": The category of the checking summary.
        - "Amount": The amount for each category.
        - "Beginning Balance": The starting balance for the statement period.
        - "Deposits and Additions": The total deposits and additions for the statement period.
        - "ATM & Debit Card Withdrawals": The total ATM and debit card withdrawals for the statement period.
        - "Electronic Withdrawals": The total electronic withdrawals for the statement period.
        - "Ending Balance": The ending balance for the statement period.
        - "Total Withdrawals": The total withdrawals for the statement period.
        - "Net Savings": The net savings for the statement period.
        - "% Saving Rate": The saving rate for the statement period.
        
        Example:
        >>> cbs_core = CBSMainCore(file_path="path/to/bank_statements")
        >>> all_checking_summaries = cbs_core.all_checking_summaries
        >>> print(all_checking_summaries)
        {
            "Date": ["2023-01-01", "2023-02-01", ...],
            "Category": ["Beginning Balance", "Deposits and Additions", ...],
            "Amount": [1000.00, 500.00, ...],
            "Beginning Balance": [1000.00, ...],
            "Deposits and Additions": [500.00, ...],
            "ATM & Debit Card Withdrawals": [200.00, ...],
            "Electronic Withdrawals": [100.00, ...],
            "Ending Balance": [1200.00, ...],
            "Total Withdrawals": [300.00, ...],
            "Net Savings": [200.00, ...],
            "% Saving Rate": [20.00, ...]
        }
        """
        pass
    
    @cached_property
    @WRAPPERS["PropertyDirOnly"]
    @WRAPPERS["SortDate"]
    @WRAPPERS["PropertyDir"]
    def all_transactions(self) -> DictOrDataFrameLike:
        """
        Returns all transactions for the bank statements in the directory.
        
        The transactions include the following columns:
        - "Date": The date of the transaction.
        - "Description": The description of the transaction.
        - "Amount": The amount of the transaction.
        - "Balance": The balance after the transaction.
        
        The transactions are structured as a DataFrame with the following columns:
        - "Date": The date of the transaction.
        - "Description": The description of the transaction.
        - "Amount": The amount of the transaction.
        - "Balance": The balance after the transaction.
        
        Example:
        >>> cbs_core = CBSMainCore(file_path="path/to/bank_statements")
        >>> all_transactions = cbs_core.all_transactions
        >>> print(all_transactions)
        {
            "Date": ["2023-01-01", "2023-01-02", ...],
            "Description": ["Purchase at Store A", "Deposit at ATM B", ...],
            "Amount": [-50.00, 100.00, ...],
            "Balance": [950.00, 1050.00, ...]
        }
        """
        pass

# endregion



__all__ = (
    "FileHandler",
    "CoreHandler",
    "CoreDirHandler",
    "CBSMainCore",
)