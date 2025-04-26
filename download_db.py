from flask import Flask, send_file, request, abort
import os

app = Flask(__name__)

# Clave secreta para proteger el endpoint (cámbiala por una clave segura)
DOWNLOAD_KEY = os.getenv("DB_DOWNLOAD_KEY", "Smile12")

@app.route("/download-db")
def download_db():
    # Verificar la clave proporcionada en los parámetros de la URL
    provided_key = request.args.get("key")
    if provided_key != DOWNLOAD_KEY:
        abort(403)  # Prohibido si la clave es incorrecta

    # Ruta del archivo de la base de datos
    db_path = os.getenv("DB_PATH", "/data/database.db")
    
    # Verificar si el archivo existe
    if not os.path.exists(db_path):
        abort(404, description="Archivo de base de datos no encontrado")
    
    # Enviar el archivo como descarga
    return send_file(db_path, as_attachment=True, download_name="database.db")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))