"""Módulo de pedidos: registro, estados y seguimiento."""
from flask import Blueprint, g, jsonify, request

from app.auth import login_required
from app.db import get_db, now_iso

bp = Blueprint("orders", __name__, url_prefix="/orders")

ESTADOS = ["recibido", "en_preparacion", "listo", "entregado", "pagado"]


def cambiar_estado(db, order_id, nuevo, user_id):
    db.execute("UPDATE orders SET status = ? WHERE id = ?", (nuevo, order_id))
    db.execute(
        "INSERT INTO order_status_history (order_id, status, changed_by, changed_at) VALUES (?, ?, ?, ?)",
        (order_id, nuevo, user_id, now_iso()))


def _detalle(db, order_id):
    pedido = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if pedido is None:
        return None
    items = db.execute(
        "SELECT oi.dish_id, d.name, oi.quantity, oi.unit_price, oi.notes FROM order_items oi "
        "JOIN dishes d ON d.id = oi.dish_id WHERE oi.order_id = ?", (order_id,)).fetchall()
    historial = db.execute(
        "SELECT status, changed_by, changed_at FROM order_status_history "
        "WHERE order_id = ? ORDER BY id", (order_id,)).fetchall()
    return {**dict(pedido), "items": [dict(i) for i in items], "history": [dict(h) for h in historial]}


@bp.post("")
@login_required("mesero", "admin")
def crear_pedido():
    data = request.get_json(silent=True) or {}
    mesa = data.get("table")
    items = data.get("items")
    if not isinstance(mesa, int) or isinstance(mesa, bool) or mesa < 1:
        return jsonify(error="La mesa es obligatoria"), 400
    if not isinstance(items, list) or not items:
        return jsonify(error="El pedido debe tener al menos un plato"), 400
    db = get_db()
    lineas, total = [], 0.0
    for item in items:
        cantidad = item.get("quantity", 1) if isinstance(item, dict) else None
        plato = db.execute("SELECT * FROM dishes WHERE id = ? AND active = 1",
                           (item.get("dish_id") if isinstance(item, dict) else None,)).fetchone()
        if plato is None or not isinstance(cantidad, int) or isinstance(cantidad, bool) or cantidad < 1:
            return jsonify(error="Plato o cantidad inválidos"), 400
        lineas.append((plato["id"], cantidad, plato["price"], item.get("notes", "")))
        total += plato["price"] * cantidad
    cur = db.execute(
        "INSERT INTO orders (table_number, customer_id, created_by, status, total, created_at) "
        "VALUES (?, ?, ?, 'recibido', ?, ?)",
        (mesa, data.get("customer_id"), g.user["id"], round(total, 2), now_iso()))
    pid = cur.lastrowid
    for dish_id, cantidad, precio, notas in lineas:
        db.execute("INSERT INTO order_items (order_id, dish_id, quantity, unit_price, notes) "
                   "VALUES (?, ?, ?, ?, ?)", (pid, dish_id, cantidad, precio, notas))
    cambiar_estado(db, pid, "recibido", g.user["id"])
    db.commit()
    return jsonify(_detalle(db, pid)), 201


@bp.get("")
@login_required("mesero", "admin")
def listar_pedidos():
    sql, params = "SELECT id, table_number, status, total, created_at FROM orders", []
    estado = request.args.get("status")
    if estado:
        sql += " WHERE status = ?"
        params.append(estado)
    filas = get_db().execute(sql + " ORDER BY id", params).fetchall()
    return jsonify([dict(f) for f in filas])


@bp.get("/<int:oid>")
@login_required()
def ver_pedido(oid):
    detalle = _detalle(get_db(), oid)
    if detalle is None:
        return jsonify(error="Pedido no encontrado"), 404
    es_personal = g.user["role"] in ("mesero", "admin")
    if not es_personal and detalle["customer_id"] != g.user["id"]:
        return jsonify(error="No tiene permisos para ver este pedido"), 403
    return jsonify(detalle)


@bp.patch("/<int:oid>/status")
@login_required("mesero", "admin")
def actualizar_estado(oid):
    nuevo = (request.get_json(silent=True) or {}).get("status")
    db = get_db()
    pedido = db.execute("SELECT status FROM orders WHERE id = ?", (oid,)).fetchone()
    if pedido is None:
        return jsonify(error="Pedido no encontrado"), 404
    if nuevo not in ESTADOS:
        return jsonify(error="Estado desconocido"), 400
    if nuevo == "pagado":
        return jsonify(error="El estado 'pagado' se asigna al registrar el cobro en caja"), 400
    if ESTADOS.index(nuevo) != ESTADOS.index(pedido["status"]) + 1:
        return jsonify(error=f"Transición no permitida: {pedido['status']} -> {nuevo}"), 409
    cambiar_estado(db, oid, nuevo, g.user["id"])
    db.commit()
    return jsonify(_detalle(db, oid))
