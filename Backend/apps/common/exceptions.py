"""Turn model-level errors raised inside views into normal 400 responses."""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import ProtectedError
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, 'error_dict') else {'detail': exc.messages}
        exc = ValidationError(detail)
    elif isinstance(exc, ProtectedError):
        exc = ValidationError({'detail': 'This record is linked to other records and cannot be deleted. '
                                         'Deactivate it instead.'})
    return drf_exception_handler(exc, context)
