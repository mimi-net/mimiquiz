import os
from urllib.parse import urlencode, urljoin, urlparse, urlunparse

from flask import request


def external_url_for(endpoint, filename=None, **kwargs):
    base = os.environ.get("EXTERNAL_BASE_URL", "localhost").rstrip("/")

    if endpoint == "static":
        endpoint = os.environ.get("STATIC_SERVER_URL", "/static").strip("/")

    endpoint = endpoint.strip("/")
    if filename is not None:
        filename = filename.strip("/")
        endpoint = f"{endpoint}/{filename}" if endpoint else filename

    path = endpoint.lstrip("/")
    query_string = urlencode(kwargs) if kwargs else ""

    full_url = urljoin(base + "/", path)
    if query_string:
        parsed = urlparse(full_url)
        full_url = urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                query_string,
                parsed.fragment,
            )
        )

    return full_url


def is_api_request():
    if (
        request.accept_mimetypes.accept_json
        and not request.accept_mimetypes.accept_html
    ):
        return True
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return True
    if request.content_type and "application/json" in request.content_type:
        return True
    return False
