def _pedido_entregado(client, mesero, plato, cantidad=1):
    pid = client.post("/orders", headers=mesero, json={
        "table": 1, "items": [{"dish_id": plato["id"], "quantity": cantidad}]}).get_json()["id"]
    for estado in ("en_preparacion", "listo", "entregado"):
        client.patch(f"/orders/{pid}/status", headers=mesero, json={"status": estado})
    return pid


def test_abrir_caja_y_rechazar_segunda_apertura(client, mesero):
    assert client.post("/cashier/open", headers=mesero, json={"opening_amount": 100000}).status_code == 201
    assert client.post("/cashier/open", headers=mesero, json={"opening_amount": 5}).status_code == 409


def test_monto_inicial_invalido(client, mesero):
    assert client.post("/cashier/open", headers=mesero, json={"opening_amount": -1}).status_code == 400


def test_cobro_requiere_caja_abierta(client, mesero, plato):
    pid = _pedido_entregado(client, mesero, plato)
    r = client.post("/cashier/payments", headers=mesero, json={"order_id": pid, "method": "efectivo"})
    assert r.status_code == 409


def test_cobro_marca_el_pedido_como_pagado(client, mesero, plato):
    client.post("/cashier/open", headers=mesero, json={"opening_amount": 0})
    pid = _pedido_entregado(client, mesero, plato)
    r = client.post("/cashier/payments", headers=mesero, json={"order_id": pid, "method": "tarjeta"})
    assert r.status_code == 201
    assert client.get(f"/orders/{pid}", headers=mesero).get_json()["status"] == "pagado"


def test_no_se_cobra_un_pedido_no_entregado(client, mesero, plato):
    client.post("/cashier/open", headers=mesero, json={"opening_amount": 0})
    pid = client.post("/orders", headers=mesero, json={
        "table": 1, "items": [{"dish_id": plato["id"], "quantity": 1}]}).get_json()["id"]
    r = client.post("/cashier/payments", headers=mesero, json={"order_id": pid, "method": "efectivo"})
    assert r.status_code == 409


def test_no_se_cobra_dos_veces(client, mesero, plato):
    client.post("/cashier/open", headers=mesero, json={"opening_amount": 0})
    pid = _pedido_entregado(client, mesero, plato)
    client.post("/cashier/payments", headers=mesero, json={"order_id": pid, "method": "efectivo"})
    r = client.post("/cashier/payments", headers=mesero, json={"order_id": pid, "method": "efectivo"})
    assert r.status_code == 409


def test_metodo_de_pago_invalido(client, mesero, plato):
    client.post("/cashier/open", headers=mesero, json={"opening_amount": 0})
    pid = _pedido_entregado(client, mesero, plato)
    assert client.post("/cashier/payments", headers=mesero,
                       json={"order_id": pid, "method": "bitcoin"}).status_code == 400


def test_cobro_de_pedido_inexistente(client, mesero):
    client.post("/cashier/open", headers=mesero, json={"opening_amount": 0})
    assert client.post("/cashier/payments", headers=mesero,
                       json={"order_id": 999, "method": "efectivo"}).status_code == 404


def test_cierre_calcula_arqueo_solo_con_efectivo(client, mesero, plato):
    client.post("/cashier/open", headers=mesero, json={"opening_amount": 100000})
    p1 = _pedido_entregado(client, mesero, plato, 1)   # 25.000 en efectivo
    p2 = _pedido_entregado(client, mesero, plato, 2)   # 50.000 con tarjeta (no entra al arqueo)
    client.post("/cashier/payments", headers=mesero, json={"order_id": p1, "method": "efectivo"})
    client.post("/cashier/payments", headers=mesero, json={"order_id": p2, "method": "tarjeta"})
    r = client.post("/cashier/close", headers=mesero, json={"counted_amount": 120000})
    assert r.status_code == 200
    cuerpo = r.get_json()
    assert cuerpo["expected_amount"] == 125000
    assert cuerpo["difference"] == -5000


def test_cierre_sin_caja_abierta(client, mesero):
    assert client.post("/cashier/close", headers=mesero, json={"counted_amount": 0}).status_code == 409


def test_cierre_valida_monto(client, mesero):
    client.post("/cashier/open", headers=mesero, json={"opening_amount": 0})
    assert client.post("/cashier/close", headers=mesero, json={"counted_amount": "x"}).status_code == 400


def test_reporte_diario(client, admin, mesero, plato):
    client.post("/cashier/open", headers=mesero, json={"opening_amount": 0})
    p1 = _pedido_entregado(client, mesero, plato, 1)
    p2 = _pedido_entregado(client, mesero, plato, 3)
    client.post("/cashier/payments", headers=mesero, json={"order_id": p1, "method": "efectivo"})
    client.post("/cashier/payments", headers=mesero, json={"order_id": p2, "method": "tarjeta"})
    r = client.get("/reports/daily", headers=admin)
    assert r.status_code == 200
    informe = r.get_json()
    assert informe["orders"] == 2
    assert informe["total_sales"] == 100000
    assert informe["average_ticket"] == 50000
    assert {m["method"]: m["total"] for m in informe["by_method"]} == {"efectivo": 25000, "tarjeta": 75000}
    assert informe["by_category"][0]["category"] == "Platos fuertes"
    assert informe["by_dish"][0]["quantity"] == 4


def test_reporte_vacio(client, admin):
    informe = client.get("/reports/daily?date=2000-01-01", headers=admin).get_json()
    assert informe["orders"] == 0 and informe["average_ticket"] == 0


def test_reporte_exporta_csv(client, admin, mesero, plato):
    client.post("/cashier/open", headers=mesero, json={"opening_amount": 0})
    pid = _pedido_entregado(client, mesero, plato, 2)
    client.post("/cashier/payments", headers=mesero, json={"order_id": pid, "method": "efectivo"})
    r = client.get("/reports/daily?format=csv", headers=admin)
    assert r.mimetype == "text/csv"
    assert "Bandeja paisa,2,50000.0" in r.get_data(as_text=True)


def test_reporte_solo_para_admin(client, mesero):
    assert client.get("/reports/daily", headers=mesero).status_code == 403
