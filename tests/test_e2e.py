"""Flujo extremo a extremo: login -> menú -> pedido -> estados -> cobro -> cierre -> reporte."""


def test_flujo_completo_de_un_servicio(client, app):
    registro = client.post("/auth/register", json={"name": "Cli", "email": "cli@correo.com",
                                                      "password": "clave1234"})
    assert registro.status_code == 201

    from tests.conftest import _crear_usuario, _login
    _crear_usuario(app, "Admin", "admin@sigr.test", "admin")
    _crear_usuario(app, "Mesero", "mesero@sigr.test", "mesero")
    admin, mesero = _login(client, "admin@sigr.test"), _login(client, "mesero@sigr.test")

    cat = client.post("/menu/categories", json={"name": "Bebidas"}, headers=admin).get_json()
    plato = client.post("/menu/dishes", headers=admin, json={
        "category_id": cat["id"], "name": "Limonada", "price": 6000}).get_json()
    assert client.get("/menu/dishes").get_json()[0]["name"] == "Limonada"

    client.post("/cashier/open", headers=mesero, json={"opening_amount": 50000})
    pedido = client.post("/orders", headers=mesero, json={
        "table": 4, "items": [{"dish_id": plato["id"], "quantity": 3}]}).get_json()
    for estado in ("en_preparacion", "listo", "entregado"):
        assert client.patch(f"/orders/{pedido['id']}/status", headers=mesero,
                            json={"status": estado}).status_code == 200
    cobro = client.post("/cashier/payments", headers=mesero,
                        json={"order_id": pedido["id"], "method": "efectivo"})
    assert cobro.status_code == 201

    cierre = client.post("/cashier/close", headers=mesero, json={"counted_amount": 68000}).get_json()
    assert cierre["expected_amount"] == 68000 and cierre["difference"] == 0

    informe = client.get("/reports/daily", headers=admin).get_json()
    assert informe["total_sales"] == 18000
    assert informe["orders"] == 1
