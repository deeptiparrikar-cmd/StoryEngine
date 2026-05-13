"""Flask app — Story Engine Sprint 1."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from backend import db
from backend.routes.episodes import bp as episodes_bp


def create_app() -> Flask:
    load_dotenv()
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    db.init_db()

    app.register_blueprint(episodes_bp, url_prefix="/api")

    @app.get("/api/health")
    def health():
        return {"ok": True}

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=True)
