from functools import cache, cached_property

from .core_handlers import CBSMainCore
from .exceptions import AnalyzerException
from .type_hints import (
    CategoryTypes,
    DataFrameLike,
    DictOrDataFrameLike,
    )
from .utils import DAY_CALENDAR, get_month_name, validate_df
from .wrappers import WRAPPERS

# ------------------------------------------------------------




MATCH_CATEGORY = WRAPPERS["MatchCategory"]




# region CoreAnalyzer
class CoreAnalyzer:
    MAIN_CORE = CBSMainCore
    CATEGORY_TYPES: CategoryTypes = (
        "summaries",
        "transactions"
    )
    SUMMARY_COLS = MAIN_CORE.checking_summary_columns["Inner"]
    TRANSACTIONS_COLS = MAIN_CORE.transaction_columns
    
    __dict__ = {}
    __slots__ = (
        "__weakrefs__",
        "_df",
        "_by_year",
        "_by_month",
        "_by_day",
        "_category",
        )
    
    def __init__(
        self,
        dataframe: DataFrameLike,
        /,
        *,
        by_year: bool = False,
        by_month: bool = False,
        by_day: bool = False,
        ) -> None:
        self._df = validate_df(dataframe)
        self._by_year = by_year
        self._by_month = by_month
        self._by_day = by_day
        
        self._category: CategoryTypes = self._category_type()
    
    @cached_property
    def _df_copy(self):
        return self._df.copy()
    
    def _category_type(self) -> CategoryTypes:
        df_cols, checking_summary_cols, transactions_cols = map(
            set,
            (
                self._df_copy.columns,
                self.SUMMARY_COLS,
                self.TRANSACTIONS_COLS
                )
            )
        
        df_issubset = df_cols.issubset
        if df_issubset(checking_summary_cols):
            category = "summaries"
        elif df_issubset(transactions_cols):
            category = "transactions"
        else:
            raise AnalyzerException(
                "`dataframe` does not match any known category (summaries | transactions). "
                f"Expected columns to match one of:"
                f"\n{checking_summary_cols = }"
                f"\n{transactions_cols = }"
                f"\nReceived columns: {df_cols!r}."
            )
        
        return category
    
    @classmethod
    def create_dataframe(cls, dataframe: DataFrameLike, **kwargs) -> DataFrameLike:
        return cls.MAIN_CORE.create_dataframe(dataframe, **kwargs)
    
    @classmethod
    def _new_df(cls, dict_stats: DictOrDataFrameLike, *, reset_index: bool = False):
        if isinstance(dict_stats, DataFrameLike):
            return dict_stats
        
        if not isinstance(dict_stats, dict):
            raise AnalyzerException(
                "`dict_stats` must be a dictionary. "
                f"Received {dict_stats!r} of type {type(dict_stats).__name__!r}."
            )
        
        
        if reset_index:
            return cls.create_dataframe(dict_stats, index_reset=True)
        
        df_dict = dict(
            zip(
                cls.MAIN_CORE.checking_summary_columns["Outer"],
                (dict_stats.keys(), dict_stats.values())
                )
            )
        return cls.MAIN_CORE.create_dataframe(df_dict)
    
    def _parse_summaries(self) -> DataFrameLike:
        summary_data = self._df_copy
        if any((self._by_year, self._by_month)):
            dt_attr = "month"  if self._by_month else "year"
            attr_col = dt_attr.title()
            summary_data['Date'] = getattr(summary_data['Date'].dt, dt_attr)
            summary_data = summary_data.rename(columns={'Date': attr_col})
            summary_stats = summary_data.groupby(attr_col).agg({
            'Beginning Balance': ['mean', 'min', 'max'],
            'Deposits and Additions': ['mean', 'sum', 'min', 'max'],
            'ATM & Debit Card Withdrawals': ['mean', 'sum'],
            'Electronic Withdrawals': ['mean', 'sum'],
            'Ending Balance': ['mean', 'last'],
            'Total Withdrawals': ['mean', 'sum'],
            'Net Savings': ['mean', 'sum'],
            '% Saving Rate': ['mean', 'max', 'min']
        })
            summary_stats.columns = [
                f"{col}_{val.title()}" if val else col
                for col, val in summary_stats.columns.to_flat_index()
                ]
            
            summary_stats = summary_stats.reset_index()
            
            if self._by_month:
                temp_col = f"{attr_col}-Temp"
                summary_stats[temp_col] = summary_stats[attr_col]
                summary_stats[attr_col] = summary_stats[temp_col].map(get_month_name)
                summary_stats = summary_stats.drop(columns=temp_col)
        else:
            summary_stats = {
                'Average Beginning Balance': summary_data['Beginning Balance'].mean(),
                'Median Beginning Balance': summary_data['Beginning Balance'].median(),
                'Max Beginning Balance': summary_data['Beginning Balance'].max(),
                'Min Beginning Balance': summary_data['Beginning Balance'].min(),
                'Average Deposits': summary_data['Deposits and Additions'].mean(),
                'Average Withdrawals': summary_data['Total Withdrawals'].mean(),
                'Average Net Savings': summary_data['Net Savings'].mean(),
                'Net Savings Volatility': summary_data['Net Savings'].std(),
                'Negative Cash Flow Months': len(summary_data[summary_data['Net Savings'] < 0])
                }
        summary_df = self._new_df(summary_stats)
        return summary_df.round(2)
    
    def _check_byargs(self) -> int:
        by_kwargs = (self._by_year, self._by_month, self._by_day)
        num_args = len([i for i in by_kwargs if i])
        if num_args > 1:
            raise AnalyzerException(
                "`by_year`, `by_month`, and `by_day` cannot be used together for this method. "
                "Please specify only one of them to group the transactions."
            )
        return num_args
    
    def _parse_transactions(self) -> DataFrameLike:
        num_args = self._check_byargs()
        if num_args == 0:
            no_args = True
        else:
            no_args = False
        
        txn_data = self._df_copy
        if any((self._by_year, self._by_month, self._by_day)):
            dt_attr = "year" if self._by_year else "month" if self._by_month else "day"
            if dt_attr == "day":
                self._by_day = True
            attr_col = dt_attr.title()
            if any((self._by_year, self._by_month)):
                txn_data['Date'] = getattr(txn_data['Date'].dt, dt_attr)
            if self._by_day:
                txn_data['Date'] = txn_data['Date'].dt.day_name()
            txn_df = txn_data.rename(columns={
                'Date': attr_col,
                'Description': 'Transactions'
                })
            txn_grouped = txn_df.groupby(attr_col).agg({
                'Amount': ['mean', 'sum'],
                'Balance': ['min', 'max', "mean"],
                'Transactions': ['count'],
            })
            txn_grouped.columns = [
                f"{col}_{val.title()}" if val else col
                for col, val in txn_grouped.columns.to_flat_index()
                ]
            
            txn_stats = txn_grouped.reset_index()
            if any((self._by_month, self._by_day)):
                temp_col_name = f'{attr_col}-Temp'
                if self._by_month:
                    txn_stats[temp_col_name] = txn_stats[attr_col].map(get_month_name)
                    txn_stats[attr_col] = txn_stats[temp_col_name]
                else:
                    cal_name_vals = {
                                    k.name.title(): k.value for k in DAY_CALENDAR
                                    }
                    txn_stats[temp_col_name] = txn_stats[attr_col].map(cal_name_vals)
                
                    txn_stats = txn_stats.sort_values(by=temp_col_name)
                
                transactions_df = txn_stats \
                                    .drop(columns=temp_col_name) \
                                    .reset_index(drop=True)
        else:
            txn_stats = {
                "Transactions": (total_txn := len(txn_data)),
                "Withdrawal Transactions": (withdrawal_txn := len(txn_data[txn_data['Amount'] < 0])),
                "Withdrawal Percent": (withdrawal_txn / total_txn) * 100,
                "Deposit Transactions": (deposit_txn := len(txn_data[txn_data['Amount'] > 0])),
                "Deposit Percent": (deposit_txn / total_txn) * 100,
                "Withdrawal-to-Deposit Ratio": (withdrawal_txn / deposit_txn),
                }
        if self._by_year or no_args:
            transactions_df = self._new_df(txn_stats)
        
        if no_args:
            transactions_df['Amount'] = transactions_df.apply(
                lambda x: (
                    f"{x['Amount']:.2f}" if "Percent" in x["Category"]
                    else f"{x['Amount']:.2f}" if "Ratio" in x["Category"]
                    else str(int(x["Amount"]))
                    ),
                axis=1
            )
        else:
            transactions_df = transactions_df.round(2)
        return transactions_df
    
    def _analyze_category(self, category: CategoryTypes, *, column: str = "", minimum: bool = False) -> DataFrameLike:
        attr_col = "Day" if self._by_day else "Month" if self._by_month else "Year"
        if attr_col == "Year":
            self._by_year = True
        
        if category == "summaries":
            txn_df = self._parse_summaries()
            if not column:
                column = "Ending Balance_Mean"
        else:
            txn_df = self._parse_transactions()
            if not column:
                column = "Transactions_Count"
        
        txn_df = txn_df.copy()
        
        if self._by_day:
            if category == "summaries":
                return txn_df
            else:
                txn_df = txn_df[~txn_df["Day"].isin(["Saturday", "Sunday"])]
        
        
        default_cols = txn_df.columns.tolist()
        valid_cols = [k for k in default_cols if '_' in k]
        cols_msg = f"\nAvailable columns are: {valid_cols!r}."
        
        
        
        if column not in default_cols:
            raise AnalyzerException(
                f"`column` {column!r} does not exist in the {category!r} DataFrame. "
                f"Please ensure that the column name is one of the aggregation columns. "
                f"{cols_msg}"
            )
        
        if "_" not in column:
            raise AnalyzerException(
                f"`column` {column!r} may not be inputted correctly or is not one of the aggregation columns. "
                "It should contain an underscore '_' to separate the column name from the aggregation type. "
                "Please ensure the column name follows the format 'ColumnName_AggregationType'."
                f"{cols_msg}"
            )
        
        
        count_df = txn_df[[attr_col, column]].loc \
                    [getattr(txn_df[column], "idxmin" if minimum else "idxmax")()]
        final_df = {
            attr_col: count_df[attr_col],
            "Minimum" if minimum else "Maximum": count_df[column]
        }
        return self._new_df(final_df, reset_index=True)
    
    def _analyze_summaries(self, *, column: str = "Ending Balance_Mean", minimum: bool = False):
        return self._analyze_category(
            "summaries",
            column=column,
            minimum=minimum
            )
    
    def _analyze_transactions(self, *, column: str = "Transactions_Count", minimum: bool = False):
        return self._analyze_category(
            "transactions",
            column=column,
            minimum=minimum
            )



# region MainAnalyzer
class CBSMainAnalyzer(CoreAnalyzer):
    def __init__(
        self,
        dataframe: DataFrameLike,
        /,
        *,
        by_year: bool = False,
        by_month: bool = False,
        by_day: bool = False,
        ) -> None:
        super().__init__(
            dataframe,
            by_year=by_year,
            by_month=by_month,
            by_day=by_day
            )
    
    @MATCH_CATEGORY("summaries", has_kwargs=True)
    @cache
    def analyze_summaries(
        self,
        *,
        column: str = "",
        minimum: bool = False
        ) -> DataFrameLike:
        """
        Analyze the checking summaries of the bank statements.
        
        Parameters:
            - column (str): The column to analyze.
            - minimum (bool): If True, return only the minimum values.
        """
        pass
    
    @MATCH_CATEGORY("transactions", has_kwargs=True)
    @cache
    def analyze_transactions(
        self,
        *,
        column: str = "",
        minimum: bool = False
        ) -> DataFrameLike:
        """
        Analyze the transactions of the bank statements.
        
        Parameters:
            - column (str): The column to analyze.
            - minimum (bool): If True, return only the minimum values.
        """
        pass



# endregion


__all__ = (
    "CoreAnalyzer",
    "CBSMainAnalyzer",
)