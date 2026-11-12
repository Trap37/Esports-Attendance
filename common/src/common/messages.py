# FIXME: This should use a class from common/schemas
def create_scan_message(scan_id: str) -> dict:
    return {
        'type': 'scan',
        'scan_id': scan_id,
        'version': 1,
    }
