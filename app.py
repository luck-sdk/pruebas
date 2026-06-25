from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text
from sqlalchemy.exc import OperationalError
import os
import logging
import time
from datetime import datetime, timedelta
import urllib.parse

app = Flask(__name__)

# ---------------------------
# CONFIGURACIÓN DE LOGGING
# ---------------------------
ENV = os.environ.get("ENV", "development")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARNING" if ENV == "production" else "INFO")
level = getattr(logging, LOG_LEVEL.upper(), logging.WARNING)
logging.basicConfig(level=level)
logger = logging.getLogger(__name__)

# ---------------------------
# CONFIGURACIÓN BASE DE DATOS
# ---------------------------
def get_connection_string():
    """Obtiene la cadena de conexión desde variables de entorno"""
    
    sql_conn = os.environ.get("SQL_CONNECTION")
    if sql_conn:
        logger.info("✅ Usando SQL_CONNECTION desde variables de entorno")
        return sql_conn
    
    server = os.environ.get("SQL_SERVER", "jhe.database.windows.net")
    database = os.environ.get("SQL_DATABASE", "jp")
    username = os.environ.get("SQL_USER", "LAPTOP-G2LDQUC8@jhe")
    password = os.environ.get("SQL_PASSWORD", "jhosue@2005")
    
    if all([server, database, username, password]):
        logger.info("✅ Usando credenciales desde variables de entorno individuales")
        params = urllib.parse.quote_plus(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER=tcp:{server},1433;"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=30;"
            "Login Timeout=30;"
        )
        return f"mssql+pyodbc:///?odbc_connect={params}"
    
    if ENV != "production":
        logger.warning("⚠️ Modo desarrollo: usando conexión local")
        params = urllib.parse.quote_plus(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=tcp:jhe.database.windows.net,1433;"
            "DATABASE=jp;"
            "UID=LAPTOP-G2LDQUC8@jhe;"
            "PWD=jhosue@2005;"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=30;"
            "Login Timeout=30;"
        )
        return f"mssql+pyodbc:///?odbc_connect={params}"
    
    logger.error("❌ No se encontraron credenciales de base de datos")
    raise Exception("Database credentials not configured")

# ---------------------------
# CONFIGURACIÓN SQLALCHEMY
# ---------------------------
SQLALCHEMY_DATABASE_URI = get_connection_string()

app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'pool_pre_ping': True,
    'pool_recycle': 120,
    'pool_size': 10,
    'max_overflow': 20,
    'pool_timeout': 30,
}

db = SQLAlchemy(app)

# ---------------------------
# MODELO
# ---------------------------
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

# ---------------------------
# CREAR TABLA (SOLO DESARROLLO)
# ---------------------------
with app.app_context():
    try:
        db.session.execute(text("SELECT 1"))
        logger.info("✅ Base de datos conectada correctamente")
        
        try:
            db.session.execute(text("SELECT TOP 1 * FROM mediciones"))
            logger.info("✅ Tabla 'mediciones' existe")
        except Exception:
            if ENV != "production":
                db.create_all()
                logger.info("📦 Tabla 'mediciones' creada")
            else:
                logger.warning("⚠️ Tabla 'mediciones' no existe en producción")
            
    except Exception as e:
        logger.error(f"❌ Error de conexión: {e}")

# ---------------------------
# DECORADOR DE REINTENTOS
# ---------------------------
def retry_db(fn, retries=3, delay=2):
    for attempt in range(retries):
        try:
            return fn()
        except OperationalError as e:
            logger.warning(f"⚠️ Intento {attempt+1}/{retries} falló: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise
        except Exception as e:
            logger.error(f"❌ Error inesperado: {e}")
            raise

# ---------------------------
# ENDPOINTS
# ---------------------------

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "OK",
        "message": "API funcionando en Azure 🚀",
        "version": "2.0",
        "environment": ENV,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route("/health", methods=["GET"])
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({
        "status": "OK",
        "message": "pong",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route("/mediciones", methods=["POST"])
def insertar():
    try:
        data = request.get_json(silent=True)
        
        if not data:
            return jsonify({"error": "JSON inválido"}), 400
        
        if "alcohol" not in data:
            return jsonify({"error": "Falta campo 'alcohol'"}), 400
        
        try:
            alcohol = float(data["alcohol"])
            if alcohol < 0:
                return jsonify({"error": "El alcohol no puede ser negativo"}), 400
            if alcohol > 100:
                return jsonify({"error": "El alcohol no puede ser mayor a 100"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Alcohol debe ser un número válido"}), 400
        
        def _insert():
            nuevo = Medicion(alcohol=alcohol)
            db.session.add(nuevo)
            db.session.commit()
            return nuevo
        
        nuevo = retry_db(_insert)
        
        logger.info(f"✅ Insertado: {alcohol}")
        
        return jsonify({
            "message": "Guardado OK",
            "data": nuevo.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error en insertar: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/mediciones", methods=["GET"])
def listar():
    try:
        def _query():
            return Medicion.query.order_by(Medicion.id.desc()).all()
        
        datos = retry_db(_query)
        
        return jsonify({
            "total": len(datos),
            "data": [d.to_dict() for d in datos],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        logger.error(f"Error en listar: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/mediciones/ultima", methods=["GET"])
def ultima():
    try:
        def _query():
            return Medicion.query.order_by(Medicion.id.desc()).first()
        
        dato = retry_db(_query)
        
        if not dato:
            return jsonify({"message": "Sin datos"}), 404
        
        return jsonify(dato.to_dict())
    except Exception as e:
        logger.error(f"Error en ultima: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/mediciones", methods=["DELETE"])
def eliminar_antiguas():
    try:
        admin_token = os.environ.get("ADMIN_TOKEN")
        if admin_token:
            token = request.headers.get("X-ADMIN-TOKEN")
            if token != admin_token:
                return jsonify({"error": "Token inválido"}), 403
        
        days = request.args.get('days', default=30, type=int)
        
        if days < 1:
            return jsonify({"error": "Los días deben ser > 0"}), 400
        
        def _delete():
            cutoff = datetime.now() - timedelta(days=days)
            count = db.session.query(Medicion).filter(
                Medicion.fecha < cutoff
            ).delete()
            db.session.commit()
            return count
        
        count = retry_db(_delete)
        
        logger.info(f"🗑️ Eliminadas {count} mediciones antiguas (>{days} días)")
        
        return jsonify({
            "message": f"Mediciones antiguas eliminadas",
            "deleted_count": count,
            "days_old": days
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error en eliminar_antiguas: {e}")
        return jsonify({"error": str(e)}), 500

# ---------------------------
# MANEJO DE ERRORES GLOBAL
# ---------------------------
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint no encontrado"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Error interno del servidor"}), 500

# ---------------------------
# MAIN
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
