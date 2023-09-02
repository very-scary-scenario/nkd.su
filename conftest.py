import pytest


@pytest.fixture(autouse=True)
def extend_doctest_namespace(doctest_namespace, transactional_db) -> None:
    pass
