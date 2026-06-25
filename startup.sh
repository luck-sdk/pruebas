#!/bin/bash
# Comando de inicio para Azure
gunicorn --bind=0.0.0.0 --timeout=300 --workers=1 wsgi:app
