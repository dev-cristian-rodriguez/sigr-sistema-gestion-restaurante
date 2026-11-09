def test_registro_crea_cliente(client):
    r = client.post("/auth/register", json={"name": "Ana", "email": "ana@correo.com", "password": "clave1234"})
    assert r.status_code == 201
    assert r.get_json()["role"] == "cliente"


def test_registro_no_permite_elegir_rol_privilegiado(client):
    r = client.post("/auth/register", json={"name": "X", "email": "x@correo.com",
                                            "password": "clave1234", "role": "admin"})
    assert r.status_code == 400


def test_registro_correo_duplicado(client):
    datos = {"name": "Ana", "email": "ana@correo.com", "password": "clave1234"}
    client.post("/auth/register", json=datos)
    assert client.post("/auth/register", json=datos).status_code == 409


def test_registro_valida_contrasena_corta(client):
    r = client.post("/auth/register", json={"name": "Ana", "email": "ana@correo.com", "password": "123"})
    assert r.status_code == 400


def test_login_exitoso_devuelve_token(client, cliente):
    r = client.get("/auth/me", headers=cliente)
    assert r.status_code == 200
    assert r.get_json()["role"] == "cliente"


def test_login_credenciales_invalidas(client, cliente):
    r = client.post("/auth/login", json={"email": "cliente@sigr.test", "password": "incorrecta"})
    assert r.status_code == 401


def test_ruta_protegida_sin_token(client):
    assert client.get("/auth/me").status_code == 401


def test_token_alterado_es_rechazado(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer token-falso"})
    assert r.status_code == 401


def test_admin_crea_mesero(client, admin):
    r = client.post("/auth/users", headers=admin, json={
        "name": "Luis", "email": "luis@sigr.test", "password": "clave1234", "role": "mesero"})
    assert r.status_code == 201
    assert r.get_json()["role"] == "mesero"


def test_cliente_no_puede_crear_usuarios_internos(client, cliente):
    r = client.post("/auth/users", headers=cliente, json={
        "name": "Luis", "email": "luis@sigr.test", "password": "clave1234", "role": "mesero"})
    assert r.status_code == 403
