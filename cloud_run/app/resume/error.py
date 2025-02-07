class SummaryParsingError(BaseException):
    def __init__(self, summaries: list[str]):
        self.summaries = summaries

    def message(self) -> str:
        return f"Number of summaries: {len(self.summaries)}"