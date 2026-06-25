from flask import Flask, jsonify
import os
import time
import flask

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "status": "OK",
        "message": "¡App funcionando en Azure 🚀",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route("/ping")
def ping():
    return jsonify({"status": "OK", "message": "pong"})

@app.route("/info")
def info():
    return jsonify({
        "python_version": os.sys.version,
        "flask_version": flask.__version__,
        "env": "Azure"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
