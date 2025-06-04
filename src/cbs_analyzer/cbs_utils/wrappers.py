from functools import partial, wraps

from .exceptions import AnalyzerException, CBSException
from .utils import PARAM_KEYWORD_ONLY, get_parameters
from .type_hints import CategoryTypes, DataFrameLike



# region FuntionWrappers
def has_core(self, attr: str = ""):
    _hasattr = hasattr(self, attr)
    if not _hasattr:
        raise CBSException(
            f"The class {self.__class__.__name__!r} does not have a core handler defined. "
            )
    return _hasattr

def reset_index(func):
    def wrapper(self):
        data = func(self)
        return data.reset_index(drop=True)
    return wrapper



# region ClassProperty
class ClassProperty:
    """
    A decorator to create a class property that can be accessed like an attribute.
    """
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, instance, owner):
        return self.fget(owner)


# region CBSWrapper
class CBSWrapper:
    def has_core(self):
        return has_core(self, "core_handler")
    
    def core_function(
        *,
        dir_property: bool = False,
        is_property: bool = False
        ):
        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                func_name = f"get_{func.__name__}"
                core = self
                _hasattr = partial(hasattr, core)
                CBSWrapper.has_core(self)
                
                if dir_property:
                    core = self.DIR_HANDLER(self._get_bank_statements())
                else:
                    if not _hasattr("_fp"):
                        raise CBSException(
                            "The class does not have a file path set. "
                            "Please ensure that the file path is set before calling this method."
                        )
                    core = self.core_handler(self._fp)
                
                if not _hasattr(func_name) and not dir_property:
                    raise CBSException(
                        f"The core handler {core = } did not return a valid function name. "
                        "Please check the core handler and try again."
                        f"\nProvided function name: {func_name!r}"
                    )
                method_results = getattr(core, func_name)
                if not is_property:
                    method_results = method_results(*args, **kwargs)
                
                if dir_property:
                    method_results = core.convert_data(method_results)
                return method_results
            return wrapper
        return decorator
    
    def files_only(*, dir_only: bool = False, is_property: bool = False):
        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                func_name = func.__name__
                expected = "directory" if dir_only else "file"
                err_msg = f"This method ({func_name!r}) is designed to work with a {expected} only."
                if hasattr(self, "_is_file") and self._is_file != (not dir_only):
                    actual = "file" if self._is_file else "directory"
                    raise CBSException(
                        f"{err_msg} "
                        f"Please provide a valid {expected} path, not a {actual} ({self._fp!r})."
                    )
                if is_property:
                    return func(self)
                return func(self, *args, **kwargs)
            return wrapper
        return decorator
    
    def get_columns():
        def decorator(func):
            @wraps(func)
            def wrapper(self):
                CBSWrapper.has_core(self)
                func_name = func.__name__.upper()
                return getattr(self.core_handler, func_name)
            return wrapper
        return decorator


# region AnalyzerWrapper
class AnalyzerWrapper:
    def df_core(self):
        core_analyzer = self.__class__.__base__
        core_analyzer_name = core_analyzer.__name__
        if core_analyzer_name != "CoreAnalyzer":
            raise AnalyzerException(
                "The class must inherit from CoreAnalyzer. "
                f"Please ensure that the class is a subclass of CoreAnalyzer, not {core_analyzer_name!r}."
            )
        return core_analyzer
    
    def sort_date():
        def decorator(func):
            @wraps(func)
            @reset_index
            def wrapper(self):
                data: DataFrameLike = func(self)
                ascending_date = False if not hasattr(self, "_ascending_date") else self._ascending_date
                return data.sort_values("Date", ascending=ascending_date)
            return wrapper
        return decorator
    
    def match_category(category: CategoryTypes, *, has_kwargs: bool = False):
        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                df_core = AnalyzerWrapper.df_core(self)
                func_name = f"_{(org_func_name := func.__name__)}"
                if not hasattr(self, "_category"):
                    raise AnalyzerException(
                        "`category` attribute is not set. "
                        f"Please ensure that the class has a valid category set before calling this method."
                    )
                if self._category != category:
                    raise AnalyzerException(
                        f"The method {org_func_name!r} is designed to work with the category {category!r}, "
                        f"but the detected category for the provided dataframe is {self._category!r}. "
                    )
                
                def _pop_kwargs(f, kwgs):
                    return {k: kwgs.pop(k, v.default) for k,v in get_parameters(f).items() if v.kind is PARAM_KEYWORD_ONLY}
                
                method_func = getattr(df_core, func_name)
                method_kwargs = _pop_kwargs(method_func, kwargs)
                if not method_kwargs:
                    return method_func(self, *args)
                
                if has_kwargs:
                    return method_func(self, *args, **method_kwargs)
                
                cls_kwargs = _pop_kwargs(df_core, kwargs)
                if not hasattr(self, "_df_copy"):
                    raise AnalyzerException(
                        f"The class {self.__class__.__name__!r} does not have a '_df_copy' method defined."
                    )
                method_func = df_core(self._df_copy(), **cls_kwargs)
                return getattr(method_func, func_name)(**method_kwargs)
            return wrapper
        return decorator


# region CoreWrappers
WRAPPERS = {
    "Columns": CBSWrapper.get_columns(),

    "Core": (CoreWrapper := CBSWrapper.core_function),
    "PropertyCore": CoreWrapper(is_property=True),
    "PropertyDir": CoreWrapper(is_property=True, dir_property=True),

    "FilesOnly": (FileOnlyWrapper := CBSWrapper.files_only),
    "PropertyFilesOnly": FileOnlyWrapper(is_property=True),

    "DirOnly": (DirOnlyWrapper := partial(CBSWrapper.files_only, dir_only=True)),
    "PropertyDirOnly": DirOnlyWrapper(is_property=True),
    "SortDate": AnalyzerWrapper.sort_date(),
    
    "MatchCategory": AnalyzerWrapper.match_category,
}


# ------------------------------------------------------------------------------------
