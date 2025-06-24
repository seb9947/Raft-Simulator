class LogEntry:
    """
    Represents a single log entry in the Raft log.
    """
    def __init__(self, term: int, command: str) -> None:
        self.term: int = term
        self.command: str = command

    def __repr__(self) -> str:
        return f"LogEntry(term={self.term}, command={self.command})"