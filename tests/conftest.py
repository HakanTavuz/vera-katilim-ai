import base64
import os
import tempfile

# must be set before anything from app/ is imported
_tmp = tempfile.mkdtemp(prefix="securebank-test-")
os.environ["DATABASE_PATH"] = os.path.join(_tmp, "test.db")
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["DATA_ENCRYPTION_KEY"] = base64.b64encode(os.urandom(32)).decode()
os.environ["DEEPSEEK_API_KEY"] = ""
os.environ["BCRYPT_ROUNDS"] = "4"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.ai.agent import assistant_limiter, clear_history  # noqa: E402
from app.auth import login_limiter  # noqa: E402
from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from scripts.seed import run_seed  # noqa: E402

# ids produced by the seed: admin is user 1, customers follow
AYSE = {"user_id": 2, "account_id": 1, "username": "ayse.yilmaz", "password": "Ayse2026!", "iban": "TR000000000000000000000001"}
MEHMET = {"user_id": 3, "account_id": 2, "username": "mehmet.kaya", "password": "Mehmet2026!", "iban": "TR000000000000000000000002"}


def _make_client(secure: bool):
    settings.SECURE_MODE = secure
    run_seed()
    login_limiter.reset()
    assistant_limiter.reset()
    for uid in range(1, 10):
        clear_history(uid)
    return TestClient(app, follow_redirects=False)


@pytest.fixture
def vuln():
    with _make_client(False) as c:
        yield c


@pytest.fixture
def secure():
    with _make_client(True) as c:
        yield c
    settings.SECURE_MODE = False


def login(client, who=AYSE):
    r = client.post("/login", data={"username": who["username"], "password": who["password"]})
    assert r.status_code == 303, r.text
    return client
