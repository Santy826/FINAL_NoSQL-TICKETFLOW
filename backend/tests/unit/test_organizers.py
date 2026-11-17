import pytest
from app.api.dependencies import get_current_user
from app.main import app


def test_crear_organizador_ok(client, mock_db, admin_user):
    app.dependency_overrides[get_current_user] = lambda: admin_user

    mock_db.organizadores.find_one.return_value = None
    mock_db.organizadores.insert_one.return_value = None

    payload = {
        "razonSocial": "Ocesa Colombia S.A.S.",
        "nit": "900555666-1",
        "contacto": "info@ocesa.co",
        "telefono": "+57 312 9998877",
        "comision": 12.0,
        "politicaDevolucion": "hasta_48h_antes",
    }

    response = client.post("/api/v1/organizers", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["razonSocial"] == "Ocesa Colombia S.A.S."
    assert data["nit"] == "900555666-1"
    assert "_id" in data


def test_crear_organizador_nit_duplicado_error(client, mock_db, admin_user):
    app.dependency_overrides[get_current_user] = lambda: admin_user
    mock_db.organizadores.find_one.return_value = {"_id": "org_previo", "nit": "900555666-1"}

    payload = {
        "razonSocial": "Otra Empresa",
        "nit": "900555666-1",
        "contacto": "otra@empresa.com",
        "comision": 10.0,
    }

    response = client.post("/api/v1/organizers", json=payload)
    assert response.status_code == 409


def test_crear_organizador_comision_invalida_error(client, admin_user):
    app.dependency_overrides[get_current_user] = lambda: admin_user

    payload = {
        "razonSocial": "Empresa",
        "nit": "900111222-3",
        "contacto": "rara@empresa.com",
        "comision": 150.0,
    }

    response = client.post("/api/v1/organizers", json=payload)
    assert response.status_code == 422


def test_crear_organizador_sin_admin_error(client, regular_user):
    app.dependency_overrides[get_current_user] = lambda: regular_user

    payload = {
        "razonSocial": "Empresa",
        "nit": "900111222-3",
        "contacto": "emp@correo.com",
        "comision": 10.0,
    }

    response = client.post("/api/v1/organizers", json=payload)
    assert response.status_code == 403


def test_obtener_organizador_no_existe_error(client, mock_db, regular_user):
    app.dependency_overrides[get_current_user] = lambda: regular_user
    mock_db.organizadores.find_one.return_value = None

    response = client.get("/api/v1/organizers/org_desconocido")
    assert response.status_code == 404
