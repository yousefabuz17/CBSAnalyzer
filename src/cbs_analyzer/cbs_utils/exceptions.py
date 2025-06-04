


class CBSException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class FileException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class AnalyzerException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class ExporterException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)