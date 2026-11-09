"""Módulo de reservas por fecha y hora, con validación de disponibilidad."""
from datetime import datetime, timedelta

from flask import Blueprint, current_app, g, jsonify, request

from app.auth import login_required
from app.db import get_db

bp = Blueprint("reservations", __name__, url_prefix="/reservations")


def _parse_inicio(data):
    try:
        return datetime.strptime(f"{data['date']} {data['time']}", "%Y-%m-%d %H:%M")
    except (KeyError, ValueError, TypeError):
        return None


@bp.post("")
@login_required()
def crear_reserva():
    cfg = current_app.config
    data = request.get_json(silent=True) or {}
    inicio = _parse_inicio(data)
    mesa, comensales = data.get("table"), data.get("guests")
    if inicio is None:
        return jsonify(error="Fecha (AAAA-MM-DD) y hora (HH:MM) válidas son obligatorias"), 400
    if not isinstance(mesa, int) or not 1 <= mesa <= cfg["TABLES"]:
        return jsonify(error=f"La mesa debe estar entre 1 y {cfg['TABLES']}"), 400
    if not isinstance(comensales, int) or not 1 <= comensales <= cfg["TABLE_CAPACITY"]:
        return jsonify(error=f"Los comensales deben estar entre 1 y {cfg['TABLE_CAPACITY']}"), 400
    if inicio < datetime.now() + timedelta(minutes=cfg["MIN_ANTICIPATION_MINUTES"]):
        return jsonify(error="La reserva requiere al menos 1 hora de anticipación"), 400
    fin = inicio + timedelta(minutes=cfg["RESERVATION_MINUTES"])
    db = get_db()
    solapada = db.execute(
        "SELECT 1 FROM reservations WHERE table_number = ? AND status = 'activa' "
        "AND start_at < ? AND end_at > ?",
        (mesa, fin.isoformat(timespec="minutes"), inicio.isoformat(timespec="minutes"))).fetchone()
    if solapada:
        return jsonify(error="La mesa ya está reservada en ese horario"), 409
    cur = db.execute(
        "INSERT INTO reservations (user_id, table_number, start_at, end_at, guests) VALUES (?, ?, ?, ?, ?)",
        (g.user["id"], mesa, inicio.isoformat(timespec="minutes"),
         fin.isoformat(timespec="minutes"), comensales))
    db.commit()
    return jsonify(id=cur.lastrowid, table=mesa, start_at=inicio.isoformat(timespec="minutes"),
                   end_at=fin.isoformat(timespec="minutes"), guests=comensales, status="activa"), 201


@bp.get("")
@login_required()
def listar_reservas():
    sql, params = "SELECT * FROM reservations", []
    if g.user["role"] == "cliente":
        sql += " WHERE user_id = ?"
        params.append(g.user["id"])
    fecha = request.args.get("date")
    if fecha:
        sql += (" AND" if params else " WHERE") + " substr(start_at, 1, 10) = ?"
        params.append(fecha)
    filas = get_db().execute(sql + " ORDER BY start_at", params).fetchall()
    return jsonify([dict(f) for f in filas])


@bp.delete("/<int:rid>")
@login_required()
def cancelar_reserva(rid):
    db = get_db()
    reserva = db.execute("SELECT * FROM reservations WHERE id = ?", (rid,)).fetchone()
    if reserva is None:
        return jsonify(error="Reserva no encontrada"), 404
    if g.user["role"] == "cliente" and reserva["user_id"] != g.user["id"]:
        return jsonify(error="No puede cancelar la reserva de otra persona"), 403
    if reserva["status"] != "activa":
        return jsonify(error="La reserva ya estaba cancelada"), 409
    db.execute("UPDATE reservations SET status = 'cancelada' WHERE id = ?", (rid,))
    db.commit()
    return jsonify(id=rid, status="cancelada")
