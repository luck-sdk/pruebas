from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text
import os
import logging
import time
import urllib.parse

app = Flask(__name__)

# ======================
# LOGGING
# ======================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ======================
# CONEXIÓN AZURE SQL (CORREGIDA)
# ======================
SQL_CONNECTION = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=tcp:jhe.database.windows.net,1433;"
    "DATABASE=jp;"
    "UID=LAPTOP-G2LDQUC8@jhe;"
    "PWD=jhosue@2005;"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=30;"
)

params = urllib.parse.quote_plus(SQL_CONNECTION)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "mssql+pyodbc:///?odbc_connect=" + params
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 1800,
    "pool_size": 5,
    "max_overflow": 10,
    "pool_timeout": 30,
}

db = SQLAlchemy(app)

# ======================
# MODELO
# ======================
class Medicion(db.Model):
    __tablename__ = "mediciones"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, server_default=func.current_timestamp())
    alcohol = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "fecha": str(self.fecha),
            "alcohol": self.alcohol
        }

# ======================
# INIT SEGURA (NO CRASHEA AZURE)
# ======================
with app.app_context():
    try:
        db.session.execute(text("SELECT 1"))
        logger.info("✅ Conexión a Azure SQL OK")
    except Exception as e:
        logger.error(f"❌ Error conexión BD: {e}")

# ======================
# ROUTES
# ======================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "OK",
        "message": "API funcionando en Azure 🚀",
        "database": "jhe.database.windows.net/jp",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })

# ======================
# INSERTAR (ESP32)
# ======================
@app.route("/mediciones", methods=["POST"])
def insertar():
    try:
        data = request.get_json()

        if not data or "alcohol" not in data:
            return jsonify({"error": "Falta alcohol"}), 400

        alcohol = float(data["alcohol"])

        if alcohol < 0 or alcohol > 100:
            return jsonify({"error": "Valor inválido (0-100)"}), 400

        nuevo = Medicion(alcohol=alcohol)
        db.session.add(nuevo)
        db.session.commit()

        logger.info(f"✅ Insertado: {alcohol}")

        return jsonify(nuevo.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error insertar: {e}")
        return jsonify({"error": str(e)}), 500

# ======================
# LISTAR
# ======================
@app.route("/mediciones", methods=["GET"])
def listar():
    try:
        datos = Medicion.query.order_by(Medicion.id.desc()).all()

        return jsonify({
            "total": len(datos),
            "data": [d.to_dict() for d in datos]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ======================
# ÚLTIMA
# ======================
@app.route("/mediciones/ultima", methods=["GET"])
def ultima():
    try:
        dato = Medicion.query.order_by(Medicion.id.desc()).first()

        if not dato:
            return jsonify({"message": "sin datos"}), 404

        return jsonify(dato.to_dict())

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ======================
# HEALTH CHECK (AZURE)
# ======================
@app.route("/health", methods=["GET"])
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({
            "status": "healthy",
            "database": "connected"
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

# ======================
# RUN
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
