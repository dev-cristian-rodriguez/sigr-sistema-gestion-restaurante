"""Módulo de autenticación: registro, login y control de acceso por rol."""
import re
from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from app.db import get_db

bp = Blueprint("auth", __name__, url_prefix="/auth")
ROLES = ("cliente", "mesero", "admin")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def _validar_usuario(data, roles_permitidos):
    nombre = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role", "cliente")
    if not nombre or not EMAIL_RE.match(email):
        return None, "Nombre y correo válidos son obligatorios"
    if len(password) < 8:
        return None, "La contraseña debe tener al menos 8 caracteres"
    if role not in roles_permitidos:
        return None, "Rol no permitido"
    return (nombre, email, password, role), None


def _crear_usuario(datos):
    nombre, email, password, role = datos
    db = get_db()
    if db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        return jsonify(error="El correo ya está registrado"), 409
    cur = db.execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
        (nombre, email, generate_password_hash(password), role))
    db.commit()
    return jsonify(id=cur.lastrowid, name=nombre, email=email, role=role), 201


def login_required(*roles):
    """Exige token válido y, si se indican roles, que el usuario tenga alguno."""
    def decorador(fn):
        @wraps(fn)
        def envoltura(*args, **kwargs):
            cabecera = request.headers.get("Authorization", "")
            if not cabecera.startswith("Bearer "):
                return jsonify(error="Autenticación requerida"), 401
            try:
                user_id = _serializer().loads(
                    cabecera[7:], max_age=current_app.config["TOKEN_MAX_AGE"])
            except (BadSignature, SignatureExpired):
                return jsonify(error="Token inválido o expirado"), 401
            user = get_db().execute(
                "SELECT id, name, email, role FROM users WHERE id = ?", (user_id,)).fetchone()
            if user is None:
                return jsonify(error="Usuario no encontrado"), 401
            if roles and user["role"] not in roles:
                return jsonify(error="No tiene permisos para esta operación"), 403
            g.user = user
            return fn(*args, **kwargs)
        return envoltura
    return decorador


@bp.post("/register")
def register():
    """Registro público: solo crea cuentas de cliente."""
    datos, error = _validar_usuario(request.get_json(silent=True) or {}, ("cliente",))
    if error:
        return jsonify(error=error), 400
    return _crear_usuario(datos)


@bp.post("/users")
@login_required("admin")
def crear_usuario_interno():
    """El administrador crea cuentas de mesero, admin o cliente."""
    datos, error = _validar_usuario(request.get_json(silent=True) or {}, ROLES)
    if error:
        return jsonify(error=error), 400
    return _crear_usuario(datos)


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if user is None or not check_password_hash(user["password_hash"], data.get("password") or ""):
        return jsonify(error="Credenciales inválidas"), 401
    return jsonify(token=_serializer().dumps(user["id"]), role=user["role"], name=user["name"])


@bp.get("/me")
@login_required()
def me():
    return jsonify(id=g.user["id"], name=g.user["name"], email=g.user["email"], role=g.user["role"])
