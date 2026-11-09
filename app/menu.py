"""Módulo de menú digital: CRUD de categorías y platos."""
import sqlite3

from flask import Blueprint, jsonify, request

from app.auth import login_required
from app.db import get_db

bp = Blueprint("menu", __name__, url_prefix="/menu")


def _fila(row):
    return dict(row) if row else None


@bp.get("/categories")
def listar_categorias():
    filas = get_db().execute("SELECT id, name FROM categories ORDER BY name").fetchall()
    return jsonify([dict(f) for f in filas])


@bp.post("/categories")
@login_required("admin")
def crear_categoria():
    nombre = ((request.get_json(silent=True) or {}).get("name") or "").strip()
    if not nombre:
        return jsonify(error="El nombre es obligatorio"), 400
    db = get_db()
    try:
        cur = db.execute("INSERT INTO categories (name) VALUES (?)", (nombre,))
    except sqlite3.IntegrityError:
        return jsonify(error="La categoría ya existe"), 409
    db.commit()
    return jsonify(id=cur.lastrowid, name=nombre), 201


@bp.put("/categories/<int:cid>")
@login_required("admin")
def editar_categoria(cid):
    nombre = ((request.get_json(silent=True) or {}).get("name") or "").strip()
    if not nombre:
        return jsonify(error="El nombre es obligatorio"), 400
    db = get_db()
    if not db.execute("SELECT 1 FROM categories WHERE id = ?", (cid,)).fetchone():
        return jsonify(error="Categoría no encontrada"), 404
    try:
        db.execute("UPDATE categories SET name = ? WHERE id = ?", (nombre, cid))
    except sqlite3.IntegrityError:
        return jsonify(error="La categoría ya existe"), 409
    db.commit()
    return jsonify(id=cid, name=nombre)


@bp.delete("/categories/<int:cid>")
@login_required("admin")
def borrar_categoria(cid):
    db = get_db()
    if db.execute("SELECT 1 FROM dishes WHERE category_id = ?", (cid,)).fetchone():
        return jsonify(error="La categoría tiene platos asociados"), 409
    cur = db.execute("DELETE FROM categories WHERE id = ?", (cid,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify(error="Categoría no encontrada"), 404
    return "", 204


@bp.get("/dishes")
def listar_platos():
    sql = "SELECT * FROM dishes WHERE active = 1"
    params = []
    categoria = request.args.get("category_id", type=int)
    if categoria:
        sql += " AND category_id = ?"
        params.append(categoria)
    filas = get_db().execute(sql + " ORDER BY name", params).fetchall()
    return jsonify([dict(f) for f in filas])


@bp.get("/dishes/<int:did>")
def ver_plato(did):
    fila = get_db().execute("SELECT * FROM dishes WHERE id = ? AND active = 1", (did,)).fetchone()
    if fila is None:
        return jsonify(error="Plato no encontrado"), 404
    return jsonify(_fila(fila))


def _validar_plato(data, parcial=False):
    errores = {}
    if not parcial or "name" in data:
        if not (data.get("name") or "").strip():
            errores["name"] = "El nombre es obligatorio"
    if not parcial or "price" in data:
        precio = data.get("price")
        if not isinstance(precio, (int, float)) or isinstance(precio, bool) or precio <= 0:
            errores["price"] = "El precio debe ser un número positivo"
    return errores


@bp.post("/dishes")
@login_required("admin")
def crear_plato():
    data = request.get_json(silent=True) or {}
    errores = _validar_plato(data)
    db = get_db()
    if not db.execute("SELECT 1 FROM categories WHERE id = ?", (data.get("category_id"),)).fetchone():
        errores["category_id"] = "La categoría no existe"
    if errores:
        return jsonify(error="Datos inválidos", detalles=errores), 400
    try:
        cur = db.execute(
            "INSERT INTO dishes (category_id, name, description, price) VALUES (?, ?, ?, ?)",
            (data["category_id"], data["name"].strip(), data.get("description", ""), data["price"]))
    except sqlite3.IntegrityError:
        return jsonify(error="Ya existe un plato con ese nombre en la categoría"), 409
    db.commit()
    fila = db.execute("SELECT * FROM dishes WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(_fila(fila)), 201


@bp.put("/dishes/<int:did>")
@login_required("admin")
def editar_plato(did):
    data = request.get_json(silent=True) or {}
    errores = _validar_plato(data, parcial=True)
    if errores:
        return jsonify(error="Datos inválidos", detalles=errores), 400
    db = get_db()
    actual = db.execute("SELECT * FROM dishes WHERE id = ? AND active = 1", (did,)).fetchone()
    if actual is None:
        return jsonify(error="Plato no encontrado"), 404
    nuevo = {k: data.get(k, actual[k]) for k in ("name", "description", "price")}
    try:
        db.execute("UPDATE dishes SET name = ?, description = ?, price = ? WHERE id = ?",
                   (nuevo["name"], nuevo["description"], nuevo["price"], did))
    except sqlite3.IntegrityError:
        return jsonify(error="Ya existe un plato con ese nombre en la categoría"), 409
    db.commit()
    return jsonify(_fila(db.execute("SELECT * FROM dishes WHERE id = ?", (did,)).fetchone()))


@bp.delete("/dishes/<int:did>")
@login_required("admin")
def borrar_plato(did):
    """Eliminación lógica: el plato deja de mostrarse pero se conserva en pedidos pasados."""
    db = get_db()
    cur = db.execute("UPDATE dishes SET active = 0 WHERE id = ? AND active = 1", (did,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify(error="Plato no encontrado"), 404
    return "", 204
