import os
import socket
from pymongo import MongoClient
from passlib.context import CryptContext

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    try:
        socket.gethostbyname("mongodb")
        MONGO_URI = "mongodb://mongodb:27017"
    except socket.gaierror:
        MONGO_URI = "mongodb://localhost:27017"

MONGO_DB = os.getenv("MONGO_DATABASE", "ticketflow")


def seed():
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]

    for col in ["recintos", "organizadores", "eventos", "usuarios"]:
        db[col].drop()

    print(f"Conectando a {MONGO_URI}/{MONGO_DB}")

    recintos = [
        {
            "_id": "rec_teatro_01",
            "nombre": "Teatro Municipal",
            "tipo": "teatro",
            "ciudad": "Cali",
            "direccion": "Cra 5 # 6-32",
            "secciones": [
                {
                    "codigo": "PLATEA",
                    "tipo": "numerada",
                    "filas": [
                        {"fila": "A", "sillas": 20},
                        {"fila": "B", "sillas": 22},
                        {"fila": "C", "sillas": 22},
                    ],
                },
                {
                    "codigo": "BALCON",
                    "tipo": "numerada",
                    "filas": [
                        {"fila": "A", "sillas": 14},
                        {"fila": "B", "sillas": 14},
                    ],
                },
                {"codigo": "GENERAL", "tipo": "general", "capacidad": 200},
            ],
            "capacidad_total": 292,
        },
        {
            "_id": "rec_estadio_01",
            "nombre": "Estadio Pascual Guerrero",
            "tipo": "estadio",
            "ciudad": "Cali",
            "direccion": "Calle 5 # 36-00",
            "secciones": [
                {
                    "codigo": "NORTE",
                    "tipo": "numerada",
                    "filas": [
                        {"fila": "1", "sillas": 50},
                        {"fila": "2", "sillas": 50},
                        {"fila": "3", "sillas": 50},
                    ],
                },
                {
                    "codigo": "SUR",
                    "tipo": "numerada",
                    "filas": [
                        {"fila": "1", "sillas": 50},
                        {"fila": "2", "sillas": 50},
                    ],
                },
                {"codigo": "ORIENTAL", "tipo": "general", "capacidad": 5000},
                {"codigo": "OCCIDENTAL", "tipo": "general", "capacidad": 3000},
            ],
            "capacidad_total": 8250,
        },
        {
            "_id": "rec_comedy_01",
            "nombre": "Sala La Quinta Bar",
            "tipo": "sala_comedia",
            "ciudad": "Bogotá",
            "direccion": "Cra 7 # 45-10",
            "secciones": [
                {
                    "codigo": "PRINCIPAL",
                    "tipo": "mesa",
                    "mesas": [
                        {"mesa": "M1", "capacidad": 6},
                        {"mesa": "M2", "capacidad": 6},
                        {"mesa": "M3", "capacidad": 4},
                        {"mesa": "M4", "capacidad": 4},
                        {"mesa": "M5", "capacidad": 8},
                    ],
                },
                {
                    "codigo": "VIP",
                    "tipo": "numerada",
                    "filas": [{"fila": "A", "sillas": 10}],
                },
            ],
            "capacidad_total": 38,
        },
    ]
    db.recintos.insert_many(recintos)
    print(f"Recintos insertados: {len(recintos)}")

    organizadores = [
        {
            "_id": "org_prod_01",
            "razonSocial": "Productora Eventos S.A.S.",
            "nit": "900123456-7",
            "contacto": "contacto@productora.com",
            "telefono": "+57 315 1234567",
            "comision": 10.0,
            "politicaDevolucion": "hasta_48h_antes",
        },
        {
            "_id": "org_comedy_01",
            "razonSocial": "Colombia Comedy Club S.A.S.",
            "nit": "901987654-3",
            "contacto": "info@colombiacomedy.com",
            "telefono": "+57 310 9876543",
            "comision": 12.5,
            "politicaDevolucion": "sin_devolucion",
        },
    ]
    db.organizadores.insert_many(organizadores)
    print(f"Organizadores insertados: {len(organizadores)}")

    eventos = [
        {
            "_id": "evt_rock_01",
            "nombre": "Concierto Rock Nacional",
            "categoria": "musica",
            "organizadorId": "org_prod_01",
            "estado": "publicado",
            "restriccionEdad": 16,
            "atributos": {
                "artistas": ["Banda X", "Grupo Y"],
                "duracionMin": 180,
                "genero": "rock",
            },
            "funciones": [
                {
                    "funcionId": "fn_rock_01",
                    "fechaHora": "2027-02-14T19:00:00-05:00",
                    "recintoId": "rec_estadio_01",
                    "ciudad": "Cali",
                    "estado": "abierta",
                    "precios": {
                        "NORTE": 250000,
                        "SUR": 200000,
                        "ORIENTAL": 80000,
                        "OCCIDENTAL": 120000,
                    },
                },
                {
                    "funcionId": "fn_rock_02",
                    "fechaHora": "2027-02-15T19:00:00-05:00",
                    "recintoId": "rec_estadio_01",
                    "ciudad": "Cali",
                    "estado": "abierta",
                    "precios": {
                        "NORTE": 250000,
                        "SUR": 200000,
                        "ORIENTAL": 80000,
                        "OCCIDENTAL": 120000,
                    },
                },
            ],
        },
        {
            "_id": "evt_comedy_01",
            "nombre": "Noche de Comedia en Vivo",
            "categoria": "comedia",
            "organizadorId": "org_comedy_01",
            "estado": "publicado",
            "restriccionEdad": 18,
            "atributos": {
                "artistas": ["Comediante A", "Comediante B"],
                "duracionMin": 120,
            },
            "funciones": [
                {
                    "funcionId": "fn_comedy_01",
                    "fechaHora": "2027-01-23T20:00:00-05:00",
                    "recintoId": "rec_comedy_01",
                    "ciudad": "Bogotá",
                    "estado": "abierta",
                    "precios": {"PRINCIPAL": 150000, "VIP": 250000},
                },
            ],
        },
    ]
    db.eventos.insert_many(eventos)
    print(f"Eventos insertados: {len(eventos)}")

    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    admin = {
        "_id": "usr_admin_01",
        "nombre": "Admin TicketFlow",
        "correo": "admin@ticketflow.com",
        "contrasenaHash": pwd.hash("Admin123!"),
        "fechaNacimiento": "1990-01-01",
        "rol": "administrador",
    }
    db.usuarios.insert_one(admin)
    print("Usuario administrador creado (admin@ticketflow.com)")

    db.usuarios.create_index("correo", unique=True)
    db.eventos.create_index([("estado", 1), ("categoria", 1), ("funciones.fechaHora", 1)])
    db.ordenes.create_index(
        "idempotencyKey",
        unique=True,
        partialFilterExpression={"idempotencyKey": {"$exists": True}},
    )
    db.boletas.create_index(
        [("funcionId", 1), ("silla", 1)],
        unique=True,
        partialFilterExpression={"estado": "valida"},
    )
    db.boletas.create_index("codigo", unique=True)
    print("Indices creados")

    print("Seed completado.")
    client.close()


if __name__ == "__main__":
    seed()
