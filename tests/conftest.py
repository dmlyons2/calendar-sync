from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_path():
    def _resolve(name: str) -> Path:
        return FIXTURE_DIR / name
    return _resolve


@pytest.fixture
def fixture_text(fixture_path):
    def _read(name: str) -> str:
        return fixture_path(name).read_text(encoding="utf-8")
    return _read
