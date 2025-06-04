import re

from pathlib import Path
from uuid import uuid4

from .exceptions import ExporterException
from .type_hints import DataFrameLike, PathLike, StringTuple
from .utils import clean_path, validate_df
from .wrappers import ClassProperty




# region Extensions
class CoreExtensions:
    DEFAULT_EXTS = {
        "csv": "to_csv",
        "xlsx": "to_excel",
        "json": "to_json",
        "parquet": "to_parquet"
    }
    
    @staticmethod
    def _validate_ext(ext: str = ""):
        if not isinstance(ext, str):
            raise ExporterException(
                f"The provided extension {ext!r} is not a valid string."
            )
        return ext
    
    @classmethod
    def _clean_ext(cls, ext: str = "", *, period_prefix: bool = False):
        new_ext = ext.removeprefix(".")
        return f'.{new_ext}' if period_prefix else new_ext
    
    @classmethod
    def _check_ext(cls, ext: str = "", *, raise_err: bool = True) -> str:
        ext = cls._validate_ext(ext)
        
        default_exts = cls.compatible_exts
        valid_exts = "|".join(re.escape(i) for i in default_exts)
        
        if not re.match(fr"^\.?({valid_exts})", ext, flags=re.IGNORECASE):
            if raise_err:
                raise ExporterException(
                    f"The provided extension {ext!r} is not supported. "
                    f"Supported extensions are:\n{default_exts}."
                    )
            return "csv"
        
        return cls._clean_ext(ext)
    
    @classmethod
    def get_ext_method(cls, ext: str = "") -> str:
        return cls.DEFAULT_EXTS[cls._check_ext(ext.lower())]
    
    @ClassProperty
    def compatible_exts(cls) -> StringTuple:
        return (*cls.DEFAULT_EXTS,)
    
    @ClassProperty
    def ext_methods(cls) -> StringTuple:
        return (*cls.DEFAULT_EXTS.values(),)
    
    @ClassProperty
    def default_exts(cls) -> dict:
        return cls.DEFAULT_EXTS




# region Exporter
class CoreExporter(CoreExtensions):
    __dict__ = {}
    __slots__ = (
        "__weakrefs__",
        "_ep",
        "_overwrite",
        "_file_found",
        "_file_ext",
        "_file_method",
    )

    def __init__(
        self,
        export_path: PathLike = "",
        *,
        overwrite: bool = True
        ):
        self._overwrite = overwrite
        
        self._ep = self._check_fp(export_path)
        self._file_found = self._check_fp(export_path, file_found=True)
        self._file_ext = self._clean_ext(self._ep.suffix)
        self._file_method = self.get_ext_method(self._file_ext)
    
    @staticmethod
    def _unique_id():
        return str(uuid4()).split("-")[0]
    
    def _check_fp(self, export_path: PathLike = "", *, file_found: bool = False) -> PathLike:
        export_path = clean_path(export_path, posix=False)
        default_file = "cbsanalyzer"
        default_extension = "csv"
        
        # Various cases for export_path:
        # 1. E.g Export path is empty ("")
        #    export_path="" -> "cbsanalyzer.csv"
        # 2. E.g Export path is a directory
        #    export_path="path/to/dir/" -> "path/to/dir/cbsanalyzer.csv"
        # 3. E.g Export path is a file name only
        #    export_path="file" -> "file.csv"
        # 4. E.g Export path is an extension type
        #    export_path=".csv" | "csv" -> "cbsanalyzer.csv"
        # 5. E.g Export path is a file with a given extension
        #    export_path="file.csv" -> "file.csv"
        # 6. E.g Export path is a hidden file name
        #    export_path="</dir/>.hidden.csv" -> "</dir/>.hidden.csv"
        # 7. E.g Export path is the current (".") or home directory ("~")
        #    export_path="." -> "</cwdir/>/cbsanalyzer.csv"
        #    export_path="~" -> "</home/>/cbsanalyzer.csv"
        
        ext_escape = "|".join(re.escape(i) for i in self.compatible_exts)
        ext = default_extension
        if not export_path:
            # E.g export_path = ""
            export_path = default_file
            ext = default_extension
        
        if re.match(r"^([.~])$", export_path):
            # E.g Export path is current or home directory
            # export_path = "." | "~"
            ext = default_extension
            if export_path.startswith("."):
                export_path = Path(export_path).cwd()
            export_path = Path(export_path).expanduser() / default_file

        elif (dir_match := re.match(r"(.*?)?\.(.*?)$", export_path)):
            if (ext_match := re.match(fr"^\.({ext_escape})?$", export_path, flags=re.IGNORECASE)):
                # E.g Export path is a valid extension type
                # export_path = ".csv"
                export_path = default_file
                ext = ext_match.group(1)
            else:
                # E.g Export path is a hidden file
                # export_path=".hidden.<...>.csv"
                ext = self._check_ext(dir_match.group(2).split(".")[-1])
                export_path = dir_match.group()[:-len(ext) + 1]
                
        elif (ext_match := re.match(fr"^({ext_escape})$", export_path)):
            # E.g Export path is a valid extension type with no period
            # export_path = "csv"
            ext = self._check_ext(ext_match.group())
            export_path = default_file
        
        # Export path currently contains no extension
        valid_fp = Path(export_path)
        
        if valid_fp.is_dir():
            ext = default_extension
            valid_fp = valid_fp / default_file
        
        ext = self._clean_ext(ext, period_prefix=True)
        
        # Export path currently contains extension
        valid_fp = valid_fp.with_suffix(ext)
        
        if valid_fp.is_file():
            found_file = True
            if not self._overwrite:
                parent = valid_fp.parent
                fp_name = valid_fp.stem
                unique_id = self._unique_id()
                new_name = "_".join((fp_name, unique_id))
                valid_fp = parent / (new_name + ext)
        else:
            found_file = False
        
        return found_file if file_found else valid_fp



# region MainExporter
class CBSMainExporter(CoreExporter):
    
    __dict__ = {}
    __slots__ = (
        "__weakrefs__",
        "_df",
        "_df_copy",
        )
    
    def __init__(
        self,
        dataframe: DataFrameLike,
        *,
        export_path: PathLike = "",
        overwrite: bool = True
        ):
        super().__init__(
            export_path,
            overwrite=overwrite
            )
        self._df = validate_df(dataframe, exception=ExporterException)
        self._df_copy = self._df.copy()
    
    def _success_msg(self) -> None:
        if all((self._file_found, self._overwrite)):
            import warnings
            warnings.warn(
                f"[WARNING] The specified file ({self._ep.name!r}) already exists and will be overwritten."
                )
        
        print(f"\nDataFrame exported successfully to {self._ep!r} using pandas method NDFrame.{self._file_method}(**to_kwargs)")
    
    def _export(self, **to_kwargs: dict) -> None:
        df = self._df_copy.map(lambda x: str(x))
        pd_to_method = getattr(df, self._file_method)
        is_json = self._file_method == "to_json"
        
        default_method_kwargs = {
            "indent" if is_json else "index": 2 if is_json else False
        }
        to_kwargs.update(default_method_kwargs)
        
        pd_to_method(
            self._ep,
            **to_kwargs
        )
        self._success_msg()

# endregion


__all__ = (
    "CoreExporter",
    "CoreExtensions",
    "CBSMainExporter"
)