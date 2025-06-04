import pandas as pd

from os import PathLike as _PathLike
from typing import (
    Iterable,
    Literal,
    Optional,
    Sequence,
    TypeAlias,
    Union
)


# Custom Type-Hints
PathLike: TypeAlias = Union[str, _PathLike]
IterablePathLike: TypeAlias = Iterable[PathLike]

DataFrame = pd.DataFrame
DataFrameLike: TypeAlias = Union[DataFrame, pd.Series]
DictOrDataFrameLike: TypeAlias = Union[DataFrameLike, dict[str, float]]

FormatTypes: TypeAlias = Literal["dataframe", "dict"]
OptionalFormatTypes: TypeAlias = Optional[FormatTypes]

IndexLike: TypeAlias = Union[
    pd.Index,
    Sequence,
    Iterable
]

# Checking-Summary & Transaction Columns
StringTuple: TypeAlias = tuple[str, ...]
NestedStringTuples: TypeAlias = dict[Literal["Outer", "Inner"], StringTuple]

CategoryTypes: TypeAlias = Literal["summaries", "transactions"]