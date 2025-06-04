import calendar
import inspect
import re
import sys

from datetime import datetime as dt
from pandas import to_datetime, to_numeric
from pathlib import Path
from string import punctuation
from typing import Any, Union

from .exceptions import CBSException, FileException
from .type_hints import DataFrameLike, PathLike



# region Constants
PARAM_KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY
DAY_CALENDAR = calendar.Day



# region Functions
def check_pyversion():
    global PY_VERSION
    PY_VERSION = tuple(
        getattr(sys.version_info, i) for i in ("major", "minor")
        )
    if not PY_VERSION >= (3, 10):
        py_v = ".".join(map(str, PY_VERSION))
        raise Exception(
            "Python version 3.10 or higher is required to run this script. "
            f"Please update your Python version {py_v!r} and try again."
        )


def clean_path(fp: PathLike, posix: bool = True) -> PathLike:
    if not isinstance(fp, PathLike):
        raise FileException(
            "The provided path is not a valid string or Path object."
            f"\nPath provided: {fp = }"
        )
    if isinstance(fp, Path):
        fp=fp.as_posix()
    
    clean_fp = fp.strip()
    return Path(clean_fp) if posix else clean_fp


def get_month_name(x: int):
    return calendar.month_name[x]


def check_fp(fp: PathLike, is_file: bool = True, raise_err: bool = True, check_is_file: bool = False) -> PathLike:
    def raise_error(isf: bool = True, original_error: str = ""):
        if check_is_file:
            return is_file
        if raise_err:
            msg = f"Invalid file path" if isf else f"Invalid folder directory"
            raise FileException(
                f"{msg} ({fp!r}). Please provide a valid path."
                f"{original_error}")
    
    if all((raise_err, check_is_file)):
        raise_err = False
    
    clean_fp=clean_path(fp, posix=False)
    if clean_fp == ".":
        if raise_err:
            raise FileException(
                f"The provided path is the current directory ({clean_fp!r}). "
                "Please provide a valid file path or directory path."
            )
        else:
            return False
        
    try:
        fp = Path(clean_fp)
    except TypeError as te:
        raise_error(original_error=te)
    
    if not is_file and fp.is_file():
        is_file = True
        
    if is_file or check_is_file:
        if not fp.is_file() and fp.is_dir():
            is_file = False
            raise_error(isf=is_file)
        else:
            is_file = True
    else:
        if not fp.is_dir():
            raise_error()
        
        if fp.is_file():
            is_file = True
    
    return is_file if check_is_file else fp


def popkwargs(*args, **kwargs) -> tuple[tuple[Any, ...], dict[str, Any]]:
    df = kwargs.pop("default_value", None)
    return *(kwargs.pop(k, df) for k in args), kwargs


def universal_date(__date, as_string: bool = False):
    universal_format = "%Y-%m-%d"
    str_date = __date.strftime(universal_format)
    if as_string:
        return str_date
    return to_datetime(str_date, errors="raise")


def extract_statement_date(statement: Path, year_only: bool = False):
    try:
        statement = clean_path(statement)
        statement_name = statement.stem
        statement_date_str = statement_name.split("-")[0]
        statement_date = dt.strptime(statement_date_str, "%Y%m%d").date()
    except:
        raise CBSException(
            f"Could not extract date from statement file name: {statement!r}. "
            "Please ensure the file name follows the format 'YYYYMMDD-...'."
        )
    
    if year_only:
        return statement_date.year
    return universal_date(statement_date)


def clean_float(x: Union[int, float, str]):
    try:
        if isinstance(x, (int, float, str)):
            x_str = str(x).strip()
            clean_punct = re.sub(r"[-.]", "", punctuation)
            punct_pat = "".join(map(re.escape, clean_punct))
            x = re.sub(fr"[{punct_pat}]", "", x_str)
    except:
        pass
    return to_numeric(x, errors="raise")


def get_parameters(func, keys_only: bool = False):
    params = {k: v for k,v in inspect.signature(func).parameters.items() if k not in ("cls", "self")}
    return (*params,) if keys_only else params


def validate_df(dataframe: DataFrameLike, exception=None) -> DataFrameLike:
    exception = exception or CBSException
    if not isinstance(dataframe, DataFrameLike):
        raise exception(
            "`dataframe` must be a pandas DataFrame. "
            f"Received {dataframe!r} of type {type(dataframe).__name__!r}."
        )
    return dataframe
# ---------------------------------------------------------------------------------------------------------