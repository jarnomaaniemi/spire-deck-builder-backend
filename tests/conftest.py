import os

import pytest


os.environ["DECKS_DB_PATH"] = "spiredb_test.db"
if os.path.exists("spiredb_test.db"):
    os.remove("spiredb_test.db")


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    yield
    if os.path.exists("spiredb_test.db"):
        os.remove("spiredb_test.db")