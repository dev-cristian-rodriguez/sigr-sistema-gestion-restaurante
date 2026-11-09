def _pedido(client, mesero, plato, cantidad=2):
    return client.post("/orders", headers=mesero, json={
        "table": 3, "items": [{"dish_id": plato["id"], "quantity": cantidad, "notes": "sin cebolla"}]})


def test_crear_pedido_calcula_total(client, mesero, plato):
    r = _pedido(client, mesero, plato)
    assert r.status_code == 201
    cuerpo = r.get_json()
    assert cuerpo["total"] == 50000
    assert cuerpo["status"] == "recibido"
    assert [h["status"] for h in cuerpo["history"]] == ["recibido"]


def test_pedido_requiere_platos(client, mesero):
    assert client.post("/orders", headers=mesero, json={"table": 1, "items": []}).status_code == 400


def test_pedido_con_plato_inexistente(client, mesero):
    r = client.post("/orders", headers=mesero, json={"table": 1, "items": [{"dish_id": 999, "quantity": 1}]})
    assert r.status_code == 400


def test_cliente_no_puede_crear_pedidos(client, cliente, plato):
    assert _pedido(client, cliente, plato).status_code == 403


def test_flujo_de_estados_en_orden(client, mesero, plato):
    pid = _pedido(client, mesero, plato).get_json()["id"]
    for estado in ("en_preparacion", "listo", "entregado"):
        r = client.patch(f"/orders/{pid}/status", headers=mesero, json={"status": estado})
        assert r.status_code == 200
        assert r.get_json()["status"] == estado
    historial = client.get(f"/orders/{pid}", headers=mesero).get_json()["history"]
    assert [h["status"] for h in historial] == ["recibido", "en_preparacion", "listo", "entregado"]


def test_no_se_puede_saltar_un_estado(client, mesero, plato):
    pid = _pedido(client, mesero, plato).get_json()["id"]
    r = client.patch(f"/orders/{pid}/status", headers=mesero, json={"status": "entregado"})
    assert r.status_code == 409


def test_estado_pagado_solo_desde_caja(client, mesero, plato):
    pid = _pedido(client, mesero, plato).get_json()["id"]
    assert client.patch(f"/orders/{pid}/status", headers=mesero, json={"status": "pagado"}).status_code == 400


def test_estado_desconocido(client, mesero, plato):
    pid = _pedido(client, mesero, plato).get_json()["id"]
    assert client.patch(f"/orders/{pid}/status", headers=mesero, json={"status": "volando"}).status_code == 400


def test_listar_pedidos_por_estado(client, mesero, plato):
    _pedido(client, mesero, plato)
    assert len(client.get("/orders?status=recibido", headers=mesero).get_json()) == 1
    assert client.get("/orders?status=listo", headers=mesero).get_json() == []


def test_pedido_inexistente(client, mesero):
    assert client.get("/orders/999", headers=mesero).status_code == 404


def test_cliente_ve_su_pedido_y_no_el_ajeno(client, app, mesero, cliente, plato):
    mi_id = client.get("/auth/me", headers=cliente).get_json()["id"]
    propio = client.post("/orders", headers=mesero, json={
        "table": 2, "customer_id": mi_id, "items": [{"dish_id": plato["id"], "quantity": 1}]}).get_json()["id"]
    ajeno = _pedido(client, mesero, plato).get_json()["id"]
    assert client.get(f"/orders/{propio}", headers=cliente).status_code == 200
    assert client.get(f"/orders/{ajeno}", headers=cliente).status_code == 403
