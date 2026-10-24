"""Pytest hooks shared by every test."""

from collections.abc import Iterator

import pytest
from tests.support import close_repositories


@pytest.fixture(autouse=True)
def _close_repositories() -> Iterator[None]:
    yield
    close_repositories()
