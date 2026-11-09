def test_crud_categorias(client, admin):
    c = client.post("/menu/categories", json={"name": "Postres"}, headers=admin)
    assert c.status_code == 201
    cid = c.get_json()["id"]
    assert client.put(f"/menu/categories/{cid}", json={"name": "Dulces"}, headers=admin).status_code == 200
    assert [x["name"] for x in client.get("/menu/categories").get_json()] == ["Dulces"]
    assert client.delete(f"/menu/categories/{cid}", headers=admin).status_code == 204


def test_categoria_duplicada(client, admin):
    client.post("/menu/categories", json={"name": "Postres"}, headers=admin)
    assert client.post("/menu/categories", json={"name": "Postres"}, headers=admin).status_code == 409


def test_no_se_borra_categoria_con_platos(client, admin, plato):
    assert client.delete(f"/menu/categories/{plato['category_id']}", headers=admin).status_code == 409


def test_crear_y_consultar_plato(client, plato):
    r = client.get(f"/menu/dishes/{plato['id']}")
    assert r.status_code == 200
    assert r.get_json()["name"] == "Bandeja paisa"


def test_lectura_del_menu_es_publica(client, plato):
    assert client.get("/menu/dishes").status_code == 200


def test_precio_debe_ser_positivo(client, admin, plato):
    r = client.post("/menu/dishes", headers=admin, json={
        "category_id": plato["category_id"], "name": "Gratis", "price": 0})
    assert r.status_code == 400


def test_nombre_unico_por_categoria(client, admin, plato):
    r = client.post("/menu/dishes", headers=admin, json={
        "category_id": plato["category_id"], "name": "Bandeja paisa", "price": 1000})
    assert r.status_code == 409


def test_editar_plato(client, admin, plato):
    r = client.put(f"/menu/dishes/{plato['id']}", headers=admin, json={"price": 27000})
    assert r.status_code == 200
    assert r.get_json()["price"] == 27000


def test_eliminacion_logica_oculta_el_plato(client, admin, plato):
    assert client.delete(f"/menu/dishes/{plato['id']}", headers=admin).status_code == 204
    assert client.get(f"/menu/dishes/{plato['id']}").status_code == 404
    assert client.get("/menu/dishes").get_json() == []


def test_escritura_restringida_a_admin(client, mesero, cliente):
    for cab in (mesero, cliente):
        assert client.post("/menu/categories", json={"name": "X"}, headers=cab).status_code == 403
    assert client.post("/menu/categories", json={"name": "X"}).status_code == 401


def test_filtrar_platos_por_categoria(client, admin, plato):
    otra = client.post("/menu/categories", json={"name": "Bebidas"}, headers=admin).get_json()["id"]
    client.post("/menu/dishes", headers=admin, json={"category_id": otra, "name": "Jugo", "price": 5000})
    r = client.get(f"/menu/dishes?category_id={otra}")
    assert [d["name"] for d in r.get_json()] == ["Jugo"]
