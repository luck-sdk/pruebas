from flask import Flask, jsonify
import os
import logging
import time
import flask

app = Flask(__name__)

# Configurar logging
logging.basicConfig(level=logging.INFO)

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "OK",
        "message": "¡App funcionando en Azure! 🚀",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0"
    })

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({
        "status": "OK",
        "message": "pong",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route("/info", methods=["GET"])
def info():
    return jsonify({
        "status": "OK",
        "python_version": os.sys.version,
        "flask_version": flask.__version__,
        "environment": "Azure App Service"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
