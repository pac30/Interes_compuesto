"""Punto de entrada.

  python app.py            -> modo desarrollo en http://127.0.0.1:5000
  FinMathLab.exe           -> ejecutable: abre el navegador solo (ver build_exe.bat)
"""
import socket
import sys
import threading
import webbrowser

from web import create_app

app = create_app()


def _free_port(preferred=5000):
    for port in range(preferred, preferred + 50):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return preferred


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        port = _free_port()
        url = f"http://127.0.0.1:{port}"
        print(f"FinMath Lab ejecutándose en {url}\nCierre esta ventana para detener la aplicación.")
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
        app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
    else:
        app.run(debug=True, port=5000)
