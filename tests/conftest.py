from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.main import create_app


@contextmanager
def make_client() -> Iterator[TestClient]:
    with TestClient(create_app()) as client:
        yield client
