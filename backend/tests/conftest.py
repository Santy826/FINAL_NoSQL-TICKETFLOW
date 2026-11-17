import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import _get_db, _get_redis, get_current_user


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def mock_redis():
    r = MagicMock()
    r.exists.return_value = True
    r.hset.return_value = True
    r.expire.return_value = True
    r.delete.return_value = True
    return r


@pytest.fixture
def admin_user():
    return {
        "_id": "usr_admin_test",
        "nombre": "Admin Tester",
        "correo": "admin@ticketflow.com",
        "fechaNacimiento": "1990-01-01",
        "rol": "administrador",
    }


@pytest.fixture
def regular_user():
    return {
        "_id": "usr_buyer_test",
        "nombre": "Comprador Tester",
        "correo": "buyer@test.com",
        "fechaNacimiento": "2000-01-01",
        "rol": "comprador",
    }


@pytest.fixture
def client(mock_db, mock_redis):
    app.dependency_overrides[_get_db] = lambda: mock_db
    app.dependency_overrides[_get_redis] = lambda: mock_redis
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
