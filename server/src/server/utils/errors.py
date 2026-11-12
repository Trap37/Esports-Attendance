from pydantic import ValidationError


def format_pydantic_validation_errors(errors: ValidationError):
    return [
        {
            'field': '.'.join(str(part) for part in error['loc']),
            'message': error['msg'],
            'type': error['type'],
        }
        for error in errors.errors()
    ]
