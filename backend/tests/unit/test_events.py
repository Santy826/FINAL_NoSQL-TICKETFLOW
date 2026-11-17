import pytest
from app.api.dependencies import get_current_user
from app.main import app


@pytest.fixture
def org_user():
    return {
        "_id": "usr_organizador_01",
        "nombre": "Organizador User",
        "correo": "org@ticketflow.com",
        "rol": "organizador",
    }


def test_crear_evento_con_funciones_ok(client, mock_db, org_user):
    app.dependency_overrides[get_current_user] = lambda: org_user

    mock_db.organizadores.find_one.return_value = {"_id": "org_01"}
    mock_db.recintos.find_one.return_value = {
        "_id": "rec_01",
        "secciones": [{"codigo": "PLATEA"}, {"codigo": "GENERAL"}],
    }
    mock_db.eventos.insert_one.return_value = None

    payload = {
        "nombre": "Festival Estéreo Picnic 2027",
        "categoria": "festival",
        "organizadorId": "org_01",
        "restriccionEdad": 18,
        "atributos": {"generos": ["indie", "rock"], "dias": 3},
        "funciones": [
            {
                "fechaHora": "2027-03-20T14:00:00-05:00",
                "recintoId": "rec_01",
                "ciudad": "Bogotá",
                "estado": "abierta",
                "precios": {"PLATEA": 450000, "GENERAL": 280000},
            }
        ],
    }

    response = client.post("/api/v1/events", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["nombre"] == "Festival Estéreo Picnic 2027"
    assert data["estado"] == "borrador"
    assert len(data["funciones"]) == 1
    assert "funcionId" in data["funciones"][0]


def test_crear_evento_organizador_no_existe_error(client, mock_db, org_user):
    app.dependency_overrides[get_current_user] = lambda: org_user
    mock_db.organizadores.find_one.return_value = None

    payload = {
        "nombre": "Evento Fantasma",
        "categoria": "musica",
        "organizadorId": "org_inexistente",
    }

    response = client.post("/api/v1/events", json=payload)
    assert response.status_code == 404


def test_crear_evento_seccion_invalida_error(client, mock_db, org_user):
    app.dependency_overrides[get_current_user] = lambda: org_user

    mock_db.organizadores.find_one.return_value = {"_id": "org_01"}
    mock_db.recintos.find_one.return_value = {
        "_id": "rec_01",
        "secciones": [{"codigo": "GENERAL"}],
    }

    payload = {
        "nombre": "Concierto",
        "categoria": "musica",
        "organizadorId": "org_01",
        "funciones": [
            {
                "fechaHora": "2027-04-10T20:00:00-05:00",
                "recintoId": "rec_01",
                "ciudad": "Cali",
                "precios": {
                    "GENERAL": 50000,
                    "VIP_INEXISTENTE": 120000,
                },
            }
        ],
    }

    response = client.post("/api/v1/events", json=payload)
    assert response.status_code == 422


def test_crear_evento_edad_negativa_error(client, org_user):
    app.dependency_overrides[get_current_user] = lambda: org_user

    payload = {
        "nombre": "Evento Invalido",
        "categoria": "teatro",
        "organizadorId": "org_01",
        "restriccionEdad": -5,
    }

    response = client.post("/api/v1/events", json=payload)
    assert response.status_code == 422


def test_cancelar_evento_ok(client, mock_db, org_user):
    app.dependency_overrides[get_current_user] = lambda: org_user
    mock_db.eventos.find_one_and_update.return_value = {
        "_id": "evt_001",
        "nombre": "Evento a cancelar",
        "estado": "cancelado",
    }

    response = client.patch("/api/v1/events/evt_001/cancel")
    assert response.status_code == 200
    assert response.json()["estado"] == "cancelado"
