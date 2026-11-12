from dataclasses import dataclass


# NOTE: Could eventually add serialization and deserialization methods here
@dataclass(frozen=True)
class ScanRequest:
    scan_id: str


@dataclass(frozen=True)
class ScanResponse:
    status: str
    message: str
    student_name: str | None = None
