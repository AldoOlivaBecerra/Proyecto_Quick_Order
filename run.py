"""
Punto de Entrada Principal para la Aplicación QUICK ORDER.
Permite ejecutar el servidor de desarrollo local ejecutando:
    python run.py
"""
import os
from app import create_app

# Obtener entorno de ejecución (por defecto 'development')
entorno = os.environ.get('QUICK_ORDER_ENV', 'development')
app = create_app(entorno)

if __name__ == '__main__':
    print("=" * 65)
    print(" >>> INICIANDO SERVIDOR WEB QUICK ORDER (Fase 1: Productos) <<<")
    print(" URL de la aplicación: http://127.0.0.1:5000")
    print(" Presione Ctrl + C en la terminal para detener el servidor.")
    print("=" * 65)
    app.run(host='127.0.0.1', port=5000, debug=True)
