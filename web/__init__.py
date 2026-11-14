from decimal import InvalidOperation, DivisionByZero, Overflow

from flask import Flask, jsonify, render_template, request, send_file

from finmath import rates, service
from finmath.validation import ValidationError, NeedsInfo
from exports import common, excel, pdf


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["JSON_AS_ASCII"] = False

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.errorhandler(ValidationError)
    def on_validation(e):
        return jsonify({"errors": e.errors, "message": e.message, "needs_info": isinstance(e, NeedsInfo)}), 422

    @app.errorhandler(ArithmeticError)
    def on_math(e):
        return jsonify({"errors": {"_": "Operación matemática inválida con los datos ingresados."},
                        "message": "Operación matemática inválida con los datos ingresados (revise tasas, plazos "
                                   "y valores).", "needs_info": False}), 422

    # ---- catálogo de tasas (configurable)
    @app.get("/api/catalog")
    def get_catalog():
        return jsonify([s.to_dict() for s in rates.load_catalog().values()])

    @app.post("/api/catalog")
    def set_catalog():
        specs = rates.save_catalog((request.get_json(silent=True) or {}).get("items"))
        return jsonify([s.to_dict() for s in specs])

    @app.post("/api/catalog/reset")
    def reset_catalog():
        return jsonify([s.to_dict() for s in rates.reset_catalog()])

    # ---- exportación (recalcula en el servidor con los mismos datos)
    @app.post("/api/export/<fmt>")
    def export(fmt):
        body = request.get_json(silent=True) or {}
        module = body.get("module")
        result = service.run_json(module, body.get("payload") or {})
        meta = {"currency": body.get("currency") or "COP", "title": common.MODULE_TITLES.get(module, module)}
        if fmt == "xlsx":
            buf = excel.build(result, meta)
            return send_file(buf, as_attachment=True, download_name=f"simulacion_{module}.xlsx",
                             mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        if fmt == "pdf":
            buf = pdf.build(result, meta)
            return send_file(buf, as_attachment=True, download_name=f"simulacion_{module}.pdf",
                             mimetype="application/pdf")
        return jsonify({"message": "Formato no soportado"}), 400

    # ---- módulos de cálculo
    @app.post("/api/<module>")
    def calculate(module):
        if module not in service.MODULES:
            return jsonify({"message": "Módulo desconocido"}), 404
        return jsonify(service.run_json(module, request.get_json(silent=True) or {}))

    return app
