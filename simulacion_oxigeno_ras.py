"""
Simulación interactiva del lazo de control de Oxígeno Disuelto en un estanque RAS
==================================================================================

Basado en el Trabajo de Investigación "Sistema de Control de Oxígeno en
Acuicultura" (UTN-BA, TA 2026). Implementa el diagrama de bloques de la
Figura 1 del informe:

        r(t) --> (+ sum -) --> e(t) --> [CONTROLADOR] --> u(t) --(+ d(t))--> [Proceso] --> y(t)
                    ^                                                                        |
                    |________________________ sensor (realimentación) ___________________|

Señales graficadas (4 paneles con ESCALAS INDEPENDIENTES: mg/L vs Hz):
    - y(t)  Respuesta (oxígeno disuelto medido), junto con r(t) y la banda de
            tolerancia (umbral inferior / superior). Si y(t) sale de esa
            banda, el sistema pasa a estado de FALLA (hipoxia o sobresaturación).
    - e(t)  Señal de error = r(t) - y(t)
    - d(t)  Perturbación aplicada (mg/L/s) — la CARGA del sistema: la demanda
            biológica de oxígeno (Rbio) que el aireador debe compensar,
            configurable en amplitud y duración.
    - u(t)  Señal de salida del controlador (frecuencia del variador),
            aplicada al proceso tras el tiempo muerto theta.

Modelo de planta: primer orden con tiempo muerto, linealizado en torno al
punto de operación (C0=7 mg/L, u0=30 Hz), sección 6.2 del informe:

    tau * d(Δy)/dt = -Δy + Kp_planta * Δu(t - theta) - d(t)

Controlador: seleccionable entre ON-OFF / P / PI / PID (ver justificación en
FUNDAMENTACION más abajo). El informe usa y recomienda PI; los demás modos
están para comparar y fundamentar esa elección.

Controles en tiempo real:
    - Tipo de controlador (radio buttons): on-off / P / PI / PID
    - Kp, Ti, Kd                  -> ganancias del controlador
    - Set-point (r)               -> referencia de OD deseada
    - Amplitud / Duración pert.   -> tamaño y duración del evento de carga (Rbio)
    - Umbral inferior / superior  -> banda de tolerancia; fuera de banda = FALLA
    - Signo de la realimentación  -> Negativa (correcta) / Positiva (demostración
                                     de por qué el lazo debe cerrarse en negativo)
    - Play/Pausa, Paso, Reset, Aplicar perturbación ahora

Requiere: matplotlib, numpy
    pip install matplotlib numpy
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, RadioButtons
from collections import deque
from matplotlib.animation import FuncAnimation

# ==========================================================================
# BLOQUE 0 · PARÁMETROS FIJOS DE LA PLANTA (Sección 6.2 del informe)
# ==========================================================================
C0_LIN = 7.0        # mg/L, punto de operación de linealización
U0 = 30.0           # Hz, punto de operación del variador
KP_PLANTA = 0.08    # (mg/L)/Hz  -> ganancia estática del proceso
TAU = 300.0         # s          -> constante de tiempo del proceso
THETA = 30.0        # s          -> tiempo muerto (retardo de transporte)
U_MIN, U_MAX = 10.0, 50.0  # Hz, límites físicos reales del variador (10-50 Hz)

# ==========================================================================
# PARÁMETROS DE LA SIMULACIÓN / ANIMACIÓN
# ==========================================================================
DT_SIM = 1.0                    # s, paso de integración interno (Euler)
SIM_SECONDS_PER_FRAME = 3.0     # s de simulación que avanzan por cada frame
FRAME_INTERVAL_MS = 50          # ms entre frames (~20 fps de dibujo)
VENTANA_S = 1200                # s de historia visible en los gráficos (20 min)


# ==========================================================================
# BLOQUE 1 · ESTADO DEL SISTEMA + PASO DE SIMULACIÓN (el lazo completo)
# ==========================================================================
class Simulacion:
    def __init__(self):
        self.reset()

    def reset(self):
        self.t = 0.0
        self.y_dev = 0.0          # desviación de y respecto de C0_LIN
        self.integral = 0.0       # acumulador del término integral
        self.prev_e = 0.0
        self.prev_y = 0.0         # para derivada sobre la medición
        self.d_filt = 0.0         # derivada filtrada
        self.onoff_state = U_MAX  # memoria del controlador on-off (histéresis)

        n_delay = max(1, int(round(THETA / DT_SIM)))
        self.delay_buffer = deque([U0] * n_delay, maxlen=n_delay)

        self.dist_rate = 0.0
        self.dist_remaining = 0.0

        self.hist_t = deque()
        self.hist_y = deque()
        self.hist_u = deque()
        self.hist_e = deque()
        self.hist_r = deque()
        self.hist_d = deque()

        self.u_actual = U0
        self.en_falla = False
        self._registrar()

    def _registrar(self):
        self.hist_t.append(self.t)
        self.hist_y.append(C0_LIN + self.y_dev)
        self.hist_u.append(self.u_actual)
        self.hist_e.append(self.prev_e)
        self.hist_r.append(params["setpoint"])
        self.hist_d.append(self.dist_rate if self.dist_remaining > 0 else 0.0)
        while self.hist_t and (self.t - self.hist_t[0]) > VENTANA_S:
            self.hist_t.popleft()
            self.hist_y.popleft()
            self.hist_u.popleft()
            self.hist_e.popleft()
            self.hist_r.popleft()
            self.hist_d.popleft()

    def disparar_perturbacion(self, amplitud_mgL, duracion_s):
        # BLOQUE 4 · PERTURBACIÓN / CARGA (Rbio): amplitud total [mg/L] y
        # duración [s] configurables -> tasa constante durante ese intervalo.
        duracion_s = max(duracion_s, 1e-3)
        self.dist_rate = amplitud_mgL / duracion_s
        self.dist_remaining = duracion_s

    def paso(self, tipo_ctrl, kp, ti, kd, setpoint, umbral_inf, umbral_sup, fb_signo):
        # -- 1.1 · SENSOR / REALIMENTACIÓN -----------------------------------
        y = C0_LIN + self.y_dev
        if fb_signo == "neg":
            e = setpoint - y                      # realimentación NEGATIVA (correcta)
        else:
            e = setpoint + (y - setpoint)          # realimentación POSITIVA (demostración: refuerza el error)

        # -- 1.2 · CONTROLADOR ------------------------------------------------
        integral_candidato = self.integral + e * DT_SIM

        if tipo_ctrl == "onoff":
            hyst = max((umbral_sup - umbral_inf) / 20.0, 0.02)
            if e > hyst:
                self.onoff_state = U_MAX
            elif e < -hyst:
                self.onoff_state = U_MIN
            u_unsat = self.onoff_state
        else:
            dydt = (y - self.prev_y) / DT_SIM
            tf = max(kd / 10.0, 1.0) if kd > 0 else 1.0
            self.d_filt += (DT_SIM / (tf + DT_SIM)) * (-dydt - self.d_filt)
            deriv_term = kp * kd * self.d_filt if (tipo_ctrl == "pid" and kd > 0) else 0.0

            prop_term = kp * e
            int_term = 0.0 if tipo_ctrl == "p" else (kp / ti) * integral_candidato
            u_unsat = U0 + prop_term + int_term + deriv_term

        u_sat = min(max(u_unsat, U_MIN), U_MAX)

        # -- 1.3 · ANTI-WINDUP (integración condicional) ----------------------
        if tipo_ctrl in ("pi", "pid"):
            would_reduce_sat = (u_unsat > U_MAX and e < 0) or (u_unsat < U_MIN and e > 0)
            if u_sat == u_unsat or would_reduce_sat:
                self.integral = integral_candidato

        self.prev_y = y
        self.prev_e = e
        self.u_actual = u_sat

        # -- 1.4 · RETARDO DE TRANSPORTE (dead time theta) --------------------
        self.delay_buffer.append(u_sat)
        u_retrasado = self.delay_buffer[0]

        # -- 1.5 · PERTURBACIÓN / CARGA activa este paso ----------------------
        dist_now = 0.0
        if self.dist_remaining > 0:
            dist_now = self.dist_rate
            self.dist_remaining -= DT_SIM

        # -- 1.6 · PROCESO / PLANTA (1er orden linealizado) -------------------
        du = u_retrasado - U0
        dydev_dt = (1.0 / TAU) * (-self.y_dev + KP_PLANTA * du) - dist_now
        self.y_dev += dydev_dt * DT_SIM

        self.t += DT_SIM
        self.en_falla = not (umbral_inf <= (C0_LIN + self.y_dev) <= umbral_sup)
        self._registrar()


# ==========================================================================
# BLOQUE 2 · PARÁMETROS AJUSTABLES DESDE EL TABLERO
# ==========================================================================
params = {
    "ctrl_type": "pi",     # "onoff" | "p" | "pi" | "pid"
    "kp": 2.5,
    "ti": 180.0,           # tiempo integral [s] (Ti=180s del informe)
    "kd": 0.0,
    "setpoint": 7.0,
    "pert_amp": 1.5,       # mg/L, caída total equivalente (evento de alimentación)
    "pert_dur": 120.0,     # s
    "umbral_inf": 5.5,     # mg/L -> banda de tolerancia inferior
    "umbral_sup": 8.5,     # mg/L -> banda de tolerancia superior
    "fb_signo": "neg",     # "neg" (correcta) | "pos" (demostración)
}

sim = Simulacion()
playing = {"on": True}   # arranca corriendo solo (autoplay), como se pidió

# ==========================================================================
# BLOQUE 3 · FIGURA Y LAYOUT — 4 gráficos apilados (y, e, d, u)
# ==========================================================================
fig = plt.figure(figsize=(14, 10))
fig.suptitle("Simulación del lazo de control de Oxígeno Disuelto (RAS)", fontsize=13)

ax_y = fig.add_axes([0.07, 0.74, 0.60, 0.19])
ax_e = fig.add_axes([0.07, 0.55, 0.60, 0.15])
ax_d = fig.add_axes([0.07, 0.36, 0.60, 0.15])
ax_u = fig.add_axes([0.07, 0.17, 0.60, 0.15])

# --- y(t): Respuesta / Salida ---
ax_y.set_ylabel("y(t) [mg/L]")
ax_y.grid(True, alpha=0.3)
ax_y.set_title("Respuesta y(t) — Oxígeno Disuelto (con banda de tolerancia)", fontsize=9, loc="left")
line_y, = ax_y.plot([], [], color="#0d6efd", lw=1.8, label="y(t) medido")
line_r, = ax_y.plot([], [], color="#6c757d", lw=1.1, ls="--", label="r(t) set-point")
line_umb_inf = ax_y.axhline(params["umbral_inf"], color="#ffc107", lw=1.2, ls=":", label="umbral falla")
line_umb_sup = ax_y.axhline(params["umbral_sup"], color="#ffc107", lw=1.2, ls=":")
banda_falla = ax_y.axhspan(params["umbral_inf"], params["umbral_sup"], color="#198754", alpha=0.08)
pto_y, = ax_y.plot([], [], "o", color="#0d6efd", ms=6)  # punto "en vivo"
ax_y.legend(loc="upper right", fontsize=7)
ax_y.set_ylim(2, 12)

# --- e(t): Error (escala propia, mucho más chica) ---
ax_e.set_ylabel("e(t) [mg/L]")
ax_e.grid(True, alpha=0.3)
ax_e.set_title("Señal de error e(t) = r(t) - y(t)", fontsize=9, loc="left")
ax_e.axhline(0, color="gray", lw=0.8)
line_e, = ax_e.plot([], [], color="#6f42c1", lw=1.5)
pto_e, = ax_e.plot([], [], "o", color="#6f42c1", ms=5)
ax_e.set_ylim(-3, 3)

# --- d(t): Perturbación / Carga ---
ax_d.set_ylabel("d(t) [mg/L·s⁻¹]")
ax_d.grid(True, alpha=0.3)
ax_d.set_title("Perturbación d(t) — carga Rbio (demanda biológica de O₂)", fontsize=9, loc="left")
ax_d.axhline(0, color="gray", lw=0.8)
line_d, = ax_d.plot([], [], color="#fd7e14", lw=1.5)
pto_d, = ax_d.plot([], [], "o", color="#fd7e14", ms=5)
ax_d.set_ylim(-0.005, 0.05)

# --- u(t): Salida del controlador (escala en Hz, no mg/L) ---
ax_u.set_ylabel("u(t) [Hz]")
ax_u.set_xlabel("tiempo [s]")
ax_u.grid(True, alpha=0.3)
ax_u.set_title("Salida del controlador u(t) — frecuencia del variador (límites 10-50 Hz)", fontsize=9, loc="left")
line_u, = ax_u.plot([], [], color="#198754", lw=1.5)
ax_u.axhline(U_MIN, color="#adb5bd", lw=1.0, ls=":")
ax_u.axhline(U_MAX, color="#adb5bd", lw=1.0, ls=":")
pto_u, = ax_u.plot([], [], "o", color="#198754", ms=5)
ax_u.set_ylim(U_MIN - 4, U_MAX + 4)

texto_estado = fig.text(0.07, 0.965, "", fontsize=10, family="monospace")
badge_vivo = fig.text(0.60, 0.965, "● EN VIVO", fontsize=9, color="#dc3545", weight="bold")

# ==========================================================================
# BLOQUE 4 · TABLERO — controles a la derecha
# ==========================================================================
def _slider_axis(y):
    return fig.add_axes([0.74, y, 0.22, 0.020])

# -- Tipo de controlador (fundamentación: comparar on-off/P/PI/PID) --
fig.text(0.74, 0.965, "Tipo de controlador", fontsize=9, weight="bold")
ax_radio = fig.add_axes([0.74, 0.905, 0.22, 0.058])
radio_ctrl = RadioButtons(ax_radio, ("on-off", "p", "pi", "pid"), active=2)

fig.text(0.74, 0.885, "Ganancias", fontsize=9, weight="bold")
s_kp = Slider(_slider_axis(0.860), "Kp", 0.0, 8.0, valinit=params["kp"])
s_ti = Slider(_slider_axis(0.825), "Ti [s]", 20.0, 600.0, valinit=params["ti"])
s_kd = Slider(_slider_axis(0.790), "Td [s]", 0.0, 120.0, valinit=params["kd"])

fig.text(0.74, 0.755, "Referencia", fontsize=9, weight="bold")
s_sp = Slider(_slider_axis(0.730), "Set-point r", 4.0, 10.0, valinit=params["setpoint"])

fig.text(0.74, 0.695, "Perturbación (carga Rbio)", fontsize=9, weight="bold")
s_amp = Slider(_slider_axis(0.670), "Amplitud [mg/L]", 0.1, 4.0, valinit=params["pert_amp"])
s_dur = Slider(_slider_axis(0.635), "Duración [s]", 5.0, 600.0, valinit=params["pert_dur"])

fig.text(0.74, 0.600, "Banda de tolerancia", fontsize=9, weight="bold")
s_uinf = Slider(_slider_axis(0.575), "Umbral inf.", 3.0, 7.0, valinit=params["umbral_inf"])
s_usup = Slider(_slider_axis(0.540), "Umbral sup.", 7.0, 11.0, valinit=params["umbral_sup"])

fig.text(0.74, 0.500, "Retroalimentación", fontsize=9, weight="bold")
ax_radio_fb = fig.add_axes([0.74, 0.455, 0.22, 0.040])
radio_fb = RadioButtons(ax_radio_fb, ("negativa (correcta)", "positiva (demo)"), active=0)


def _actualizar_ctrl_type(label):
    params["ctrl_type"] = {"on-off": "onoff", "p": "p", "pi": "pi", "pid": "pid"}[label]
radio_ctrl.on_clicked(_actualizar_ctrl_type)

def _actualizar_fb(label):
    params["fb_signo"] = "neg" if label.startswith("negativa") else "pos"
radio_fb.on_clicked(_actualizar_fb)

def _actualizar_kp(v): params["kp"] = v
def _actualizar_ti(v): params["ti"] = max(v, 1.0)
def _actualizar_kd(v): params["kd"] = v
def _actualizar_sp(v): params["setpoint"] = v
def _actualizar_amp(v): params["pert_amp"] = v
def _actualizar_dur(v): params["pert_dur"] = v


def _redibujar_banda():
    global banda_falla
    banda_falla.remove()
    banda_falla = ax_y.axhspan(params["umbral_inf"], params["umbral_sup"], color="#198754", alpha=0.08)


def _actualizar_uinf(v):
    params["umbral_inf"] = v
    line_umb_inf.set_ydata([v, v])
    _redibujar_banda()


def _actualizar_usup(v):
    params["umbral_sup"] = v
    line_umb_sup.set_ydata([v, v])
    _redibujar_banda()


s_kp.on_changed(_actualizar_kp)
s_ti.on_changed(_actualizar_ti)
s_kd.on_changed(_actualizar_kd)
s_sp.on_changed(_actualizar_sp)
s_amp.on_changed(_actualizar_amp)
s_dur.on_changed(_actualizar_dur)
s_uinf.on_changed(_actualizar_uinf)
s_usup.on_changed(_actualizar_usup)

# -- Botones: Play/Pausa, Paso, Reset, Aplicar perturbación --
ax_play = fig.add_axes([0.74, 0.395, 0.10, 0.040])
ax_step = fig.add_axes([0.855, 0.395, 0.105, 0.040])
ax_reset = fig.add_axes([0.74, 0.345, 0.10, 0.040])
ax_pert = fig.add_axes([0.855, 0.345, 0.105, 0.040])

b_play = Button(ax_play, "⏸ Pausar")
b_step = Button(ax_step, "⏭ Paso")
b_reset = Button(ax_reset, "↺ Reset")
b_pert = Button(ax_pert, "⚡ Aplicar\npert.")


def _toggle_play(event):
    playing["on"] = not playing["on"]
    b_play.label.set_text("⏸ Pausar" if playing["on"] else "▶ Correr")


def _reset(event):
    sim.reset()
    playing["on"] = True                 # autoplay también tras el reset
    b_play.label.set_text("⏸ Pausar")


def _un_paso(event):
    sim.paso(params["ctrl_type"], params["kp"], params["ti"], params["kd"],
             params["setpoint"], params["umbral_inf"], params["umbral_sup"], params["fb_signo"])
    fig.canvas.draw_idle()


def _aplicar_perturbacion(event):
    sim.disparar_perturbacion(params["pert_amp"], params["pert_dur"])


b_play.on_clicked(_toggle_play)
b_step.on_clicked(_un_paso)
b_reset.on_clicked(_reset)
b_pert.on_clicked(_aplicar_perturbacion)

# ==========================================================================
# BLOQUE 5 · FUNDAMENTACIÓN (texto de apoyo para el informe)
# ==========================================================================
FUNDAMENTACION = """
FUNDAMENTACION
--------------
Por que PI y no otro controlador:
  - On-off: conmuta 10/50 Hz segun el signo del error. Nunca se estabiliza
    (oscila permanentemente / chattering), desgasta el variador y el
    soplador -> viola el objetivo de eficiencia energetica.
  - P: reacciona rapido pero necesita error distinto de cero para sostener
    una salida distinta de u0. Con la carga sostenida de Rbio el lazo abierto
    es Tipo 0 -> error de estado estacionario NO nulo (offset permanente).
  - PI (elegido): el polo integrador (1/Ti*s) hace al lazo abierto Tipo 1 ->
    e_ss=0 ante el escalon de referencia y ante la carga constante (Rbio),
    que son los dos escenarios reales del estanque.
  - PID: con theta/tau = 30/300 = 0.1 (retardo chico frente a tau), la
    derivada aporta poca mejora de velocidad y amplifica ruido de alta
    frecuencia de la sonda, sumando un parametro mas para sintonizar sin
    beneficio claro.

Cual es la carga del sistema:
  Rbio, la demanda biologica de oxigeno de la biomasa (consumo respiratorio
  de los peces), analoga a una carga electrica que el aireador debe
  abastecer en todo momento. Se modela como d(t): un escalon temporal de
  amplitud y duracion configurables que se resta del balance de masa.

Retroalimentacion negativa vs positiva:
  Con e = r - y (negativa), un desvio genera una accion que empuja a y de
  vuelta hacia r: el lazo converge. Con e = r + (y - r) (positiva, solo
  demostrativa), el mismo controlador hace diverger la señal: el error se
  retroalimenta reforzandose a si mismo. Esta comparacion justifica por que
  todo lazo realimentado debe cerrarse con signo negativo.

Cuidado con las escalas:
  y(t)/r(t) en mg/L (rango ~4-10), e(t) en mg/L pero de magnitud mucho menor
  (+-0.5 a +-2.5 tipico), u(t) en Hz (10-50) y d(t) en mg/L/s (escala muy
  chica). Por eso se grafican en 4 paneles con ejes independientes: mezclar
  Hz con mg/L en un solo eje "aplasta" visualmente variaciones reales.
"""
print(FUNDAMENTACION)

# ==========================================================================
# BLOQUE 6 · MOTOR DE ANIMACION EN TIEMPO REAL
# ==========================================================================
def _update(frame):
    if playing["on"]:
        pasos = max(1, int(SIM_SECONDS_PER_FRAME / DT_SIM))
        for _ in range(pasos):
            sim.paso(params["ctrl_type"], params["kp"], params["ti"], params["kd"],
                      params["setpoint"], params["umbral_inf"], params["umbral_sup"],
                      params["fb_signo"])

    t = list(sim.hist_t)
    line_y.set_data(t, list(sim.hist_y))
    line_r.set_data(t, list(sim.hist_r))
    line_e.set_data(t, list(sim.hist_e))
    line_d.set_data(t, list(sim.hist_d))
    line_u.set_data(t, list(sim.hist_u))

    if t:
        xlim = (t[0], max(t[-1], t[0] + 10))
        for ax in (ax_y, ax_e, ax_d, ax_u):
            ax.set_xlim(*xlim)
        # puntos "en vivo" en el ultimo valor de cada serie
        pto_y.set_data([t[-1]], [sim.hist_y[-1]])
        pto_e.set_data([t[-1]], [sim.hist_e[-1]])
        pto_d.set_data([t[-1]], [sim.hist_d[-1]])
        pto_u.set_data([t[-1]], [sim.hist_u[-1]])

    # el badge "EN VIVO" parpadea en cada frame, corriendo o pausado
    badge_vivo.set_alpha(0.35 + 0.65 * abs(np.sin(frame / 6.0)))

    y_now = sim.hist_y[-1] if sim.hist_y else C0_LIN
    e_now = sim.hist_e[-1] if sim.hist_e else 0.0
    u_now = sim.hist_u[-1] if sim.hist_u else U0
    d_now = sim.hist_d[-1] if sim.hist_d else 0.0

    if sim.en_falla:
        estado = "FALLA (fuera de umbral)"
        color_estado = "#dc3545"
        line_y.set_color("#dc3545")
    elif params["fb_signo"] == "pos":
        estado = "DIVERGIENDO (realimentacion positiva)"
        color_estado = "#dc3545"
        line_y.set_color("#dc3545")
    else:
        estado = "NORMAL (dentro de banda tolerada)"
        color_estado = "#198754"
        line_y.set_color("#0d6efd")

    texto_estado.set_text(
        f"t={sim.t:7.1f}s  ctrl={params['ctrl_type']:5s}  r={params['setpoint']:.2f}  "
        f"y={y_now:5.2f}mg/L  e={e_now:+5.2f}mg/L  u={u_now:5.1f}Hz  "
        f"d={d_now:+.4f}mg/L·s⁻¹   |   Estado: {estado}"
    )
    texto_estado.set_color(color_estado)

    return line_y, line_r, line_e, line_d, line_u, pto_y, pto_e, pto_d, pto_u, texto_estado, badge_vivo


anim = FuncAnimation(fig, _update, interval=FRAME_INTERVAL_MS, blit=False, cache_frame_data=False)

# Perturbación de demostración automática ~3s después de abrir la figura,
# para ver el lazo reaccionar sin tocar nada primero.
def _demo_inicial():
    if playing["on"]:
        sim.disparar_perturbacion(params["pert_amp"], params["pert_dur"])

fig.canvas.new_timer(interval=3000, callbacks=[(_demo_inicial, [], {})]).start()

if __name__ == "__main__":
    plt.show()