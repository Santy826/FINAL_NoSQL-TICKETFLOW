import pytest
from app.api.dependencies import get_current_user
from app.main import app


def test_crear_recinto_teatro_ok(client, mock_db, admin_user):
    app.dependency_overrides[get_current_user] = lambda: admin_user

    payload = {
        "nombre": "Teatro Municipal de Cali",
        "tipo": "teatro",
        "ciudad": "Cali",
        "direccion": "Cra 5 # 6-32",
        "secciones": [
            {
                "codigo": "PLATEA",
                "tipo": "numerada",
                "filas": [{"fila": "A", "sillas": 20}, {"fila": "B", "sillas": 22}],
            },
            {
                "codigo": "GENERAL",
                "tipo": "general",
                "capacidad": 150,
            },
        ],
    }

    mock_db.recintos.insert_one.return_value = None

    response = client.post("/api/v1/venues", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["nombre"] == "Teatro Municipal de Cali"
    assert data["capacidad_total"] == 192
    assert "_id" in data


def test_crear_recinto_mesas_ok(client, mock_db, admin_user):
    app.dependency_overrides[get_current_user] = lambda: admin_user

    payload = {
        "nombre": "Comedy Club Central",
        "tipo": "sala_comedia",
        "ciudad": "Bogotá",
        "secciones": [
            {
                "codigo": "MESAS_VIP",
                "tipo": "mesa",
                "mesas": [{"mesa": "M1", "capacidad": 4}, {"mesa": "M2", "capacidad": 6}],
            }
        ],
    }

    mock_db.recintos.insert_one.return_value = None

    response = client.post("/api/v1/venues", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["capacidad_total"] == 10


def test_crear_recinto_secciones_duplicadas_error(client, mock_db, admin_user):
    app.dependency_overrides[get_current_user] = lambda: admin_user

    payload = {
        "nombre": "Recinto Invalido",
        "tipo": "teatro",
        "ciudad": "Medellín",
        "secciones": [
            {"codigo": "ZONA_A", "tipo": "general", "capacidad": 50},
            {"codigo": "ZONA_A", "tipo": "general", "capacidad": 100},
        ],
    }

    response = client.post("/api/v1/venues", json=payload)
    assert response.status_code == 422


def test_crear_recinto_capacidad_negativa_error(client, mock_db, admin_user):
    app.dependency_overrides[get_current_user] = lambda: admin_user

    payload = {
        "nombre": "Estadio Invalido",
        "tipo": "estadio",
        "ciudad": "Barranquilla",
        "secciones": [{"codigo": "GENERAL", "tipo": "general", "capacidad": -20}],
    }

    response = client.post("/api/v1/venues", json=payload)
    assert response.status_code == 422


def test_crear_recinto_sin_admin_error(client, regular_user):
    app.dependency_overrides[get_current_user] = lambda: regular_user

    payload = {
        "nombre": "Teatro Test",
        "tipo": "teatro",
        "ciudad": "Cali",
        "secciones": [{"codigo": "GEN", "tipo": "general", "capacidad": 100}],
    }

    response = client.post("/api/v1/venues", json=payload)
    assert response.status_code == 403


def test_obtener_recinto_no_existe_error(client, mock_db, regular_user):
    app.dependency_overrides[get_current_user] = lambda: regular_user
    mock_db.recintos.find_one.return_value = None

    response = client.get("/api/v1/venues/rec_no_existe")
    assert response.status_code == 404
