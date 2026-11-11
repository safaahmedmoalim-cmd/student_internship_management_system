import mimetypes
import os

from django.http import FileResponse, Http404


def file_download(field_file, download_name=None):
    """Stream a private upload back to an authorised user."""
    if not field_file:
        raise Http404('No file attached.')
    try:
        handle = field_file.open('rb')
    except FileNotFoundError:
        raise Http404('The file is missing on the server.')
    name = download_name or os.path.basename(field_file.name)
    content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
    return FileResponse(handle, as_attachment=True, filename=name, content_type=content_type)
