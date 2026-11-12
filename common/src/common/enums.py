from enum import StrEnum


class MessageType(StrEnum):
    SCAN = 'scan'
    SCAN_RESPONSE = 'scan_response'
    ERROR = 'error'


class ScanStatus(StrEnum):
    SUCCESS = 'success'
    STUDENT_NOT_FOUND = 'student_not_found'
    ERROR = 'error'
