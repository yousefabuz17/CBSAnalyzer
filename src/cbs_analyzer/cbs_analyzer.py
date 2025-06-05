from .cbs_utils.core_handlers import CBSMainCore
from .cbs_utils.core_analyzers import CBSMainAnalyzer
from .cbs_utils.core_exporter import CoreExtensions, CBSMainExporter
from .cbs_utils.type_hints import DataFrame, DataFrameLike, PathLike



class CBSExporter(CBSMainExporter):
    __dict__ = {}
    __slots__ = ("_df",)

    def __init__(self, dataframe: DataFrameLike):
        self._df = dataframe

    def export(self, export_path="", overwrite=True, **to_kwargs) -> None:
        """
        Acceptable values for the `export_path` parameter in exporters.

        1. Empty string:
            - "" → will save as "cbsanalyzer.csv" in current directory.

        2. Directory path:
            - "path/to/dir/" → saves as "path/to/dir/cbsanalyzer.csv"

        3. File name only:
            - "file" → resolves to "file.csv"

        4. Extension only:
            - ".csv" or "csv" → resolves to "cbsanalyzer.csv"

        5. File with extension:
            - "file.csv" → resolves to "file.csv"

        6. Hidden file:
            - ".hidden.csv" → resolves to ".hidden.csv"
            - "path/.hidden.csv" → resolves to "path/.hidden.csv"

        7. Special directory symbols:
            - "." → resolves to "<current_working_directory>/cbsanalyzer.csv"
            - "~" → resolves to "<home_directory>/cbsanalyzer.csv"
        """
        super().__init__(self._df, export_path=export_path, overwrite=overwrite)
        return self._export(**to_kwargs)


class CBSDataFrame(DataFrame):
    @property
    def _constructor(self):
        return CBSDataFrame

    def export(self, *args, **kwargs):
        CBSExporter(self).export(*args, **kwargs)


class CBSAnalyzer(CBSMainCore, CoreExtensions):
    MAIN_ANALYZER = CBSMainAnalyzer

    def __init__(self, file_path: PathLike, *, ascending_date: bool = False) -> None:
        super().__init__(file_path, ascending_date=ascending_date)

    def __getattribute__(self, name):
        value = super().__getattribute__(name)

        # Avoid wrapping class-level constants and callables
        if isinstance(value, DataFrame) and not isinstance(value, CBSDataFrame):
            try:
                return CBSDataFrame(value)
            except:
                pass  # Fallback if conversion fails
        return value

    def analyze_summaries(
        self,
        *,
        by_year=False,
        by_month=False,
        by_day=False,
        column: str = "",
        minimum: bool = False
    ):
        """
        Analyze the checking summaries of the bank statements.

        Parameters:
            - by_year (bool): If True, analyze by year.
            - by_month (bool): If True, analyze by month.
            - by_day (bool): If True, analyze by day.
            - column (str): The column to analyze.
            - minimum (bool): If True, return only the minimum values.

        Returns:
            - Analyzed summaries based on the specified parameters.
        """
        return self.MAIN_ANALYZER(
            self.all_checking_summaries,
            by_year=by_year,
            by_month=by_month,
            by_day=by_day,
        ).analyze_summaries(column=column, minimum=minimum)

    def analyze_transactions(
        self,
        *,
        by_year=False,
        by_month=False,
        by_day=False,
        column: str = "",
        minimum: bool = False
    ):
        """
        Analyze the transactions of the bank statements.

        Parameters:
            - by_year (bool): If True, analyze by year.
            - by_month (bool): If True, analyze by month.
            - by_day (bool): If True, analyze by day.
            - column (str): The column to analyze.
            - minimum (bool): If True, return only the minimum values.

        Returns:
            - Analyzed transactions based on the specified parameters.
        """
        return self.MAIN_ANALYZER(
            self.all_transactions, by_year=by_year, by_month=by_month, by_day=by_day
        ).analyze_transactions(column=column, minimum=minimum)


__all__ = (
    "CBSAnalyzer",
    "CBSExporter",
    "CBSDataFrame",
)