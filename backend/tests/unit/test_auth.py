import pytest
from app.core.security import hash_password
from app.api.dependencies import get_current_user
from app.main import app


def test_registro_usuario_ok(client, mock_db):
    mock_db.usuarios.find_one.return_value = None
    mock_db.usuarios.insert_one.return_value = None

    payload = {
        "nombre": "Carlos Gómez",
        "correo": "carlos@correo.com",
        "contrasena": "ClaveSegura123!",
        "fechaNacimiento": "1998-07-20",
        "rol": "comprador",
    }

    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["correo"] == "carlos@correo.com"
    assert "_id" in data
    assert "contrasena" not in data
    assert "contrasenaHash" not in data


def test_registro_correo_duplicado_error(client, mock_db):
    mock_db.usuarios.find_one.return_value = {"_id": "usr_existente", "correo": "duplicado@correo.com"}

    payload = {
        "nombre": "Duplicado",
        "correo": "duplicado@correo.com",
        "contrasena": "ClaveSegura123!",
        "fechaNacimiento": "1995-01-01",
        "rol": "comprador",
    }

    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


def test_registro_datos_invalidos_error(client):
    payload = {
        "nombre": "Invalido",
        "correo": "no-es-correo",
        "contrasena": "123",
        "fechaNacimiento": "2000-01-01",
        "rol": "comprador",
    }

    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


def test_login_ok(client, mock_db, mock_redis):
    clave = "SuperSecret123!"
    mock_db.usuarios.find_one.return_value = {
        "_id": "usr_100",
        "nombre": "Ana López",
        "correo": "ana@correo.com",
        "contrasenaHash": hash_password(clave),
        "fechaNacimiento": "1992-03-10",
        "rol": "comprador",
    }

    payload = {"correo": "ana@correo.com", "contrasena": clave}

    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["usuario"]["correo"] == "ana@correo.com"
    mock_redis.hset.assert_called_once()
    mock_redis.expire.assert_called_once()


def test_login_clave_incorrecta_error(client, mock_db):
    mock_db.usuarios.find_one.return_value = {
        "_id": "usr_100",
        "correo": "ana@correo.com",
        "contrasenaHash": hash_password("ClaveReal123"),
    }

    payload = {"correo": "ana@correo.com", "contrasena": "ClaveEquivocada"}

    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401


def test_logout_ok(client, mock_redis, regular_user):
    app.dependency_overrides[get_current_user] = lambda: regular_user

    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": "Bearer token_test_123"},
    )
    assert response.status_code == 204
    mock_redis.delete.assert_called_once_with("sesion:token_test_123")
