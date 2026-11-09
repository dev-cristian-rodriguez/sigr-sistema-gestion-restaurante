from datetime import date, timedelta

MAÑANA = (date.today() + timedelta(days=1)).isoformat()


def _reservar(client, headers, mesa=1, hora="20:00", comensales=2, fecha=MAÑANA):
    return client.post("/reservations", headers=headers, json={
        "table": mesa, "date": fecha, "time": hora, "guests": comensales})


def test_crear_reserva(client, cliente):
    r = _reservar(client, cliente)
    assert r.status_code == 201
    cuerpo = r.get_json()
    assert cuerpo["start_at"] == f"{MAÑANA}T20:00"
    assert cuerpo["end_at"] == f"{MAÑANA}T21:30"


def test_no_permite_solapamiento_en_la_misma_mesa(client, cliente):
    _reservar(client, cliente, hora="20:00")
    assert _reservar(client, cliente, hora="21:00").status_code == 409


def test_misma_hora_en_otra_mesa_es_valida(client, cliente):
    _reservar(client, cliente, mesa=1)
    assert _reservar(client, cliente, mesa=2).status_code == 201


def test_horario_contiguo_es_valido(client, cliente):
    _reservar(client, cliente, hora="20:00")
    assert _reservar(client, cliente, hora="21:30").status_code == 201


def test_requiere_una_hora_de_anticipacion(client, cliente):
    r = _reservar(client, cliente, fecha=date.today().isoformat(), hora="00:00")
    assert r.status_code == 400


def test_valida_capacidad_y_mesa(client, cliente):
    assert _reservar(client, cliente, comensales=9).status_code == 400
    assert _reservar(client, cliente, mesa=99).status_code == 400


def test_valida_formato_de_fecha(client, cliente):
    assert _reservar(client, cliente, fecha="31/12/2030").status_code == 400


def test_reserva_requiere_autenticacion(client):
    assert _reservar(client, {}).status_code == 401


def test_cancelar_libera_la_mesa(client, cliente):
    rid = _reservar(client, cliente).get_json()["id"]
    assert client.delete(f"/reservations/{rid}", headers=cliente).status_code == 200
    assert _reservar(client, cliente).status_code == 201


def test_cancelar_dos_veces(client, cliente):
    rid = _reservar(client, cliente).get_json()["id"]
    client.delete(f"/reservations/{rid}", headers=cliente)
    assert client.delete(f"/reservations/{rid}", headers=cliente).status_code == 409


def test_cliente_solo_ve_y_cancela_las_suyas(client, app, cliente, mesero):
    rid = _reservar(client, cliente).get_json()["id"]
    assert len(client.get("/reservations", headers=cliente).get_json()) == 1
    assert len(client.get("/reservations", headers=mesero).get_json()) == 1
    otro = client.post("/auth/register", json={"name": "O", "email": "o@correo.com", "password": "clave1234"})
    token = client.post("/auth/login", json={"email": "o@correo.com", "password": "clave1234"}).get_json()["token"]
    ajeno = {"Authorization": f"Bearer {token}"}
    assert client.get("/reservations", headers=ajeno).get_json() == []
    assert client.delete(f"/reservations/{rid}", headers=ajeno).status_code == 403
    assert otro.status_code == 201


def test_cancelar_reserva_inexistente(client, cliente):
    assert client.delete("/reservations/999", headers=cliente).status_code == 404


def test_filtrar_por_fecha(client, cliente):
    _reservar(client, cliente)
    assert len(client.get(f"/reservations?date={MAÑANA}", headers=cliente).get_json()) == 1
    assert client.get("/reservations?date=2000-01-01", headers=cliente).get_json() == []
