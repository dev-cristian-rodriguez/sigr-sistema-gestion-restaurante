import pytest

from app import create_app
from app.db import get_db
from werkzeug.security import generate_password_hash


@pytest.fixture
def app(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True})
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _crear_usuario(app, name, email, role, password="clave1234"):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (name, email, generate_password_hash(password), role),
        )
        db.commit()


def _login(client, email, password="clave1234"):
    r = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.get_json()['token']}"}


@pytest.fixture
def admin(app, client):
    _crear_usuario(app, "Admin", "admin@sigr.test", "admin")
    return _login(client, "admin@sigr.test")


@pytest.fixture
def mesero(app, client):
    _crear_usuario(app, "Mesero", "mesero@sigr.test", "mesero")
    return _login(client, "mesero@sigr.test")


@pytest.fixture
def cliente(app, client):
    _crear_usuario(app, "Cliente", "cliente@sigr.test", "cliente")
    return _login(client, "cliente@sigr.test")


@pytest.fixture
def plato(client, admin):
    """Una categoría y un plato listos para usar en las pruebas."""
    c = client.post("/menu/categories", json={"name": "Platos fuertes"}, headers=admin)
    d = client.post("/menu/dishes", headers=admin, json={
        "category_id": c.get_json()["id"], "name": "Bandeja paisa", "price": 25000})
    return d.get_json()
