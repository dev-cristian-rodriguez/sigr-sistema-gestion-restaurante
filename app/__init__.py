"""SIGR: Sistema Integral de Gestión de Restaurante."""
import os

from flask import Flask, jsonify

from app import db


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-secret-cambiar-en-produccion"),
        DATABASE=os.getenv("DATABASE", "sigr.db"),
        TOKEN_MAX_AGE=3600,
        TABLES=10,
        TABLE_CAPACITY=4,
        RESERVATION_MINUTES=90,
        MIN_ANTICIPATION_MINUTES=60,
    )
    if config:
        app.config.update(config)

    app.teardown_appcontext(db.close_db)
    with app.app_context():
        db.init_db()

    from app import auth
    for modulo in (auth,):
        app.register_blueprint(modulo.bp)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify(error="Recurso no encontrado"), 404

    return app
