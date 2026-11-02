import pytest

from src.data_gen import generate
from src.db import build_connection


@pytest.fixture(scope="session")
def con(tmp_path_factory):
    d = tmp_path_factory.mktemp("data")
    generate(d)
    return build_connection(d)
