"""Módulo de cierre de caja (apertura, cobros, arqueo) y reportes de ventas."""
import csv
import io
from datetime import date

from flask import Blueprint, Response, g, jsonify, request

from app.auth import login_required
from app.db import get_db, now_iso
from app.orders import cambiar_estado

bp = Blueprint("cashier", __name__)
METODOS = ("efectivo", "tarjeta", "transferencia")


def _caja_abierta(db):
    return db.execute("SELECT * FROM cash_registers WHERE closed_at IS NULL").fetchone()


def _numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool) and valor >= 0


@bp.post("/cashier/open")
@login_required("mesero", "admin")
def abrir_caja():
    monto = (request.get_json(silent=True) or {}).get("opening_amount")
    if not _numero(monto):
        return jsonify(error="El monto inicial debe ser un número mayor o igual a 0"), 400
    db = get_db()
    if _caja_abierta(db):
        return jsonify(error="Ya existe una caja abierta"), 409
    cur = db.execute("INSERT INTO cash_registers (opened_by, opening_amount, opened_at) VALUES (?, ?, ?)",
                     (g.user["id"], monto, now_iso()))
    db.commit()
    return jsonify(id=cur.lastrowid, opening_amount=monto), 201


@bp.post("/cashier/payments")
@login_required("mesero", "admin")
def registrar_cobro():
    data = request.get_json(silent=True) or {}
    db = get_db()
    caja = _caja_abierta(db)
    if caja is None:
        return jsonify(error="No hay una caja abierta"), 409
    if data.get("method") not in METODOS:
        return jsonify(error="Método de pago inválido"), 400
    pedido = db.execute("SELECT * FROM orders WHERE id = ?", (data.get("order_id"),)).fetchone()
    if pedido is None:
        return jsonify(error="Pedido no encontrado"), 404
    if pedido["status"] != "entregado":
        return jsonify(error="Solo se pueden cobrar pedidos entregados"), 409
    db.execute("INSERT INTO payments (order_id, register_id, method, amount, paid_at) VALUES (?, ?, ?, ?, ?)",
               (pedido["id"], caja["id"], data["method"], pedido["total"], now_iso()))
    cambiar_estado(db, pedido["id"], "pagado", g.user["id"])
    db.commit()
    return jsonify(order_id=pedido["id"], method=data["method"], amount=pedido["total"]), 201


@bp.post("/cashier/close")
@login_required("mesero", "admin")
def cerrar_caja():
    contado = (request.get_json(silent=True) or {}).get("counted_amount")
    if not _numero(contado):
        return jsonify(error="El monto contado debe ser un número mayor o igual a 0"), 400
    db = get_db()
    caja = _caja_abierta(db)
    if caja is None:
        return jsonify(error="No hay una caja abierta"), 409
    efectivo = db.execute("SELECT COALESCE(SUM(amount), 0) FROM payments "
                          "WHERE register_id = ? AND method = 'efectivo'", (caja["id"],)).fetchone()[0]
    esperado = round(caja["opening_amount"] + efectivo, 2)
    diferencia = round(contado - esperado, 2)
    db.execute("UPDATE cash_registers SET closed_at = ?, counted_amount = ?, expected_amount = ?, difference = ? "
               "WHERE id = ?", (now_iso(), contado, esperado, diferencia, caja["id"]))
    db.commit()
    return jsonify(expected_amount=esperado, counted_amount=contado, difference=diferencia)


@bp.get("/reports/daily")
@login_required("admin")
def reporte_diario():
    fecha = request.args.get("date") or date.today().isoformat()
    db = get_db()
    resumen = db.execute("SELECT COUNT(*) AS n, COALESCE(SUM(amount), 0) AS total FROM payments "
                         "WHERE substr(paid_at, 1, 10) = ?", (fecha,)).fetchone()
    por_metodo = db.execute("SELECT method, SUM(amount) AS total FROM payments "
                            "WHERE substr(paid_at, 1, 10) = ? GROUP BY method ORDER BY method", (fecha,)).fetchall()
    por_categoria = db.execute(
        "SELECT c.name AS category, SUM(oi.quantity * oi.unit_price) AS total FROM payments p "
        "JOIN order_items oi ON oi.order_id = p.order_id JOIN dishes d ON d.id = oi.dish_id "
        "JOIN categories c ON c.id = d.category_id WHERE substr(p.paid_at, 1, 10) = ? "
        "GROUP BY c.name ORDER BY c.name", (fecha,)).fetchall()
    por_plato = db.execute(
        "SELECT d.name AS dish, SUM(oi.quantity) AS quantity, SUM(oi.quantity * oi.unit_price) AS total "
        "FROM payments p JOIN order_items oi ON oi.order_id = p.order_id JOIN dishes d ON d.id = oi.dish_id "
        "WHERE substr(p.paid_at, 1, 10) = ? GROUP BY d.name ORDER BY d.name", (fecha,)).fetchall()
    pedidos, total = resumen["n"], round(resumen["total"], 2)
    informe = {
        "date": fecha, "orders": pedidos, "total_sales": total,
        "average_ticket": round(total / pedidos, 2) if pedidos else 0,
        "by_method": [dict(r) for r in por_metodo],
        "by_category": [dict(r) for r in por_categoria],
        "by_dish": [dict(r) for r in por_plato],
    }
    if request.args.get("format") == "csv":
        salida = io.StringIO()
        w = csv.writer(salida)
        w.writerow(["plato", "cantidad", "total"])
        for fila in informe["by_dish"]:
            w.writerow([fila["dish"], fila["quantity"], fila["total"]])
        return Response(salida.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename=ventas-{fecha}.csv"})
    return jsonify(informe)
