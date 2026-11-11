"""Upload validation shared by every module that accepts documents."""
import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils.deconstruct import deconstructible

DOCUMENT_EXTENSIONS = ['pdf', 'doc', 'docx']
ATTACHMENT_EXTENSIONS = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'xlsx', 'pptx']

document_extension_validator = FileExtensionValidator(DOCUMENT_EXTENSIONS)
attachment_extension_validator = FileExtensionValidator(ATTACHMENT_EXTENSIONS)


def validate_upload_size(file):
    limit = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file.size > limit:
        raise ValidationError(f'File is larger than {settings.MAX_UPLOAD_SIZE_MB} MB.')


@deconstructible
class UploadTo:
    """Store uploads as <folder>/<owner id>/<random name>.<ext> so original names never hit the disk."""

    def __init__(self, folder, owner_field='student_id'):
        self.folder = folder
        self.owner_field = owner_field

    def __call__(self, instance, filename):
        ext = os.path.splitext(filename)[1].lower()
        owner = getattr(instance, self.owner_field, None) or 'misc'
        return f'{self.folder}/{owner}/{uuid.uuid4().hex}{ext}'

    def __eq__(self, other):
        return isinstance(other, UploadTo) and (self.folder, self.owner_field) == (other.folder, other.owner_field)
