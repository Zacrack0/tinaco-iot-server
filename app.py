from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import os

app = Flask(__name__)

estado = {
    "distancia": None,
    "porcentaje": None,
    "litros_aproximados": None,
    "ultima_actualizacion": None,
    "alerta": None,
    "dias_restantes": None,
    "recomendacion": None
}

historial = []

# Configuración del tinaco (ajusta según tu caso)
CAPACIDAD_LITROS = 750        # capacidad total del tinaco
NIVEL_CRITICO = 10
NIVEL_BAJO = 20
NIVEL_ALTO = 95


def calcular_litros(porcentaje):
    return round((porcentaje / 100) * CAPACIDAD_LITROS, 1)


def calcular_dias_restantes():
    """Predicción simple basada en el consumo de las últimas lecturas"""
    if len(historial) < 3:
        return None

    # Tomar últimas lecturas con porcentaje
    recientes = [h for h in historial[-20:] if h.get("porcentaje") is not None]
    if len(recientes) < 3:
        return None

    # Calcular consumo promedio por hora (muy básico)
    try:
        p1 = recientes[0]["porcentaje"]
        p2 = recientes[-1]["porcentaje"]
        t1 = datetime.fromisoformat(recientes[0]["fecha"])
        t2 = datetime.fromisoformat(recientes[-1]["fecha"])

        horas = (t2 - t1).total_seconds() / 3600
        if horas <= 0:
            return None

        consumo_porcentaje = p1 - p2
        if consumo_porcentaje <= 0:
            return None  # no hay consumo o se llenó

        consumo_por_hora = consumo_porcentaje / horas
        if consumo_por_hora <= 0:
            return None

        porcentaje_actual = recientes[-1]["porcentaje"]
        horas_restantes = porcentaje_actual / consumo_por_hora
        dias = round(horas_restantes / 24, 1)
        return max(dias, 0)
    except:
        return None


def generar_recomendacion(porcentaje, dias):
    if porcentaje is None:
        return "Esperando datos del sensor."
    if porcentaje <= NIVEL_CRITICO:
        return "Nivel crítico. Llena el tinaco lo antes posible."
    if porcentaje <= NIVEL_BAJO:
        return "Nivel bajo. Te recomiendo programar el llenado hoy."
    if dias is not None and dias < 1.5:
        return f"Según tu consumo, el agua podría alcanzarte menos de {dias} días."
    if porcentaje >= NIVEL_ALTO:
        return "Nivel alto. Revisa que no haya desbordamiento."
    return "Nivel estable. Todo en orden."


@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "TinacoIoT Server activo", "estado": estado})


@app.route("/nivel", methods=["POST"])
def recibir_nivel():
    try:
        dist_str = request.form.get("distancia")
        porc_str = request.form.get("porcentaje")

        if not dist_str or not porc_str:
            return jsonify({"error": "Faltan datos"}), 400

        distancia = float(dist_str)
        porcentaje = round(float(porc_str), 1)
        litros = calcular_litros(porcentaje)

        # Alerta
        alerta = None
        if porcentaje <= NIVEL_CRITICO:
            alerta = f"¡CRÍTICO! Nivel muy bajo: {porcentaje}%"
        elif porcentaje <= NIVEL_BAJO:
            alerta = f"Nivel bajo: {porcentaje}%"
        elif porcentaje >= NIVEL_ALTO:
            alerta = f"Nivel alto: {porcentaje}%. Posible desbordamiento"

        # Guardar historial
        registro = {
            "distancia": distancia,
            "porcentaje": porcentaje,
            "litros": litros,
            "alerta": alerta,
            "fecha": datetime.now().isoformat()
        }
        historial.append(registro)
        if len(historial) > 200:
            historial.pop(0)

        # Predicción y recomendación
        dias = calcular_dias_restantes()
        recomendacion = generar_recomendacion(porcentaje, dias)

        # Actualizar estado
        estado.update({
            "distancia": distancia,
            "porcentaje": porcentaje,
            "litros_aproximados": litros,
            "ultima_actualizacion": registro["fecha"],
            "alerta": alerta,
            "dias_restantes": dias,
            "recomendacion": recomendacion
        })

        print(f"→ {porcentaje}% | {litros} L | días: {dias} | {alerta}")

        return jsonify({
            "ok": True,
            "porcentaje": porcentaje,
            "litros": litros,
            "dias_restantes": dias,
            "alerta": alerta,
            "recomendacion": recomendacion
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/estado", methods=["GET"])
def estado_actual():
    return jsonify(estado)


@app.route("/historial", methods=["GET"])
def obtener_historial():
    return jsonify(historial[-50:])


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)