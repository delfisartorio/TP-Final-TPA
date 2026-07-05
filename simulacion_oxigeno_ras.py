"""
Simulación interactiva del lazo de control de Oxígeno Disuelto en un estanque RAS
==================================================================================

Basado en el Trabajo de Investigación "Sistema de Control de Oxígeno en
Acuicultura" (UTN-BA, TA 2026). Implementa el diagrama de bloques de la
Figura 1 del informe:

        r(t) --> (+ sum -) --> e(t) --> [PID] --> u(t) --(+ d(t))--> [Proceso] --> y(t)
                    ^                                                              |
                    |______________________ sensor (realimentación) ______________|

Se grafican por separado las 4 señales del lazo:
    - y(t)  Respuesta (oxígeno disuelto medido), junto con r(t) y la banda de
            tolerancia (umbral inferior / superior). Si y(t) sale de esa
            banda, el sistema pasa a estado de FALLA (ej. hipoxia severa o
            sobresaturación crítica).
    - e(t)  Señal de error = r(t) - y(t)
    - d(t)  Perturbación aplicada (mg/L por segundo, evento de biomasa /
            alimentación / temperatura)
    - u(t)  Señal de entrada al proceso (frecuencia del variador, calculada
            por el PID y aplicada tras el tiempo muerto)

Modelo de planta: primer orden con tiempo muerto, linealizado en torno al
punto de operación (C0 = 7 mg/L, u0 = 30 Hz), sección 6.2 del informe:

    tau * d(Δy)/dt = -Δy + Kp_planta * Δu(t - theta) - d(t)

Controlador: PID con anti-windup por clamping (el informe usa PI; se deja Kd
disponible para experimentar).

Controles en tiempo real (sliders/botones):
    - Kp, Ki, Kd                 -> ganancias del controlador
    - Set-point (r)              -> referencia de OD deseada
    - Amplitud / Duración pert.  -> tamaño y duración del evento de perturbación
    - Umbral inferior / superior -> banda de OD considerada "error tolerable";
                                     fuera de esa banda se declara FALLA
    - Play / Pausa, Reset, Aplicar perturbación

Requiere: matplotlib, numpy
    pip install matplotlib numpy
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from collections import deque
from matplotlib.animation import FuncAnimation

# ------------------------------------------------------------------
# Parámetros físicos del proceso (Sección 6.2 del informe)
# ------------------------------------------------------------------
C0_LIN = 7.0        # mg/L, punto de operación de linealización
U0 = 30.0           # Hz, punto de operación del variador
KP_PLANTA = 0.08    # (mg/L)/Hz  -> ganancia estática del proceso
TAU = 300.0         # s          -> constante de tiempo del proceso
THETA = 30.0        # s          -> tiempo muerto
U_MIN, U_MAX = 0.0, 50.0   # Hz, límites físicos del variador

# ------------------------------------------------------------------
# Parámetros de la simulación
# ------------------------------------------------------------------
DT_SIM = 1.0                    # s, paso de integración interno
SIM_SECONDS_PER_FRAME = 3.0     # s de simulación que avanzan por cada frame
FRAME_INTERVAL_MS = 50          # ms entre frames (velocidad de reproducción)
VENTANA_S = 1800                # s de historia visible en los gráficos (30 min)


class Simulacion:
    def __init__(self):
        self.reset()

    def reset(self):
        self.t = 0.0
        self.y_dev = 0.0
        self.integral = 0.0
        self.prev_e = 0.0

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
        duracion_s = max(duracion_s, 1e-3)
        self.dist_rate = amplitud_mgL / duracion_s
        self.dist_remaining = duracion_s

    def paso(self, kp, ki, kd, setpoint, umbral_inf, umbral_sup):
        y = C0_LIN + self.y_dev
        e = setpoint - y

        derivative = (e - self.prev_e) / DT_SIM
        integral_candidato = self.integral + e * DT_SIM

        u_unsat = U0 + kp * e + ki * integral_candidato + kd * derivative
        u_sat = min(max(u_unsat, U_MIN), U_MAX)

        if u_sat == u_unsat or (u_sat >= U_MAX and e < 0) or (u_sat <= U_MIN and e > 0):
            self.integral = integral_candidato

        self.prev_e = e
        self.u_actual = u_sat

        self.delay_buffer.append(u_sat)
        u_retrasado = self.delay_buffer[0]

        dist_now = 0.0
        if self.dist_remaining > 0:
            dist_now = self.dist_rate
            self.dist_remaining -= DT_SIM

        du = u_retrasado - U0
        dydev_dt = (1.0 / TAU) * (-self.y_dev + KP_PLANTA * du) - dist_now
        self.y_dev += dydev_dt * DT_SIM

        self.t += DT_SIM
        self.en_falla = not (umbral_inf <= (C0_LIN + self.y_dev) <= umbral_sup)
        self._registrar()


# ------------------------------------------------------------------
# Estado global de parámetros ajustables (sliders escriben acá)
# ------------------------------------------------------------------
params = {
    "kp": 2.5,
    "ki": 2.5 / 180.0,     # equivalente a Ti = 180 s del informe
    "kd": 0.0,
    "setpoint": 7.0,
    "pert_amp": -1.5,      # mg/L (negativo = caída, ej. evento de alimentación)
    "pert_dur": 300.0,     # s
    "umbral_inf": 5.0,     # mg/L -> por debajo: hipoxia severa / FALLA
    "umbral_sup": 9.0,     # mg/L -> por encima: sobresaturación crítica / FALLA
}

sim = Simulacion()
playing = {"on": False}

# ------------------------------------------------------------------
# Figura y layout: 4 gráficos apilados (y, e, d, u)
# ------------------------------------------------------------------
fig = plt.figure(figsize=(13, 10))
fig.suptitle("Simulación del lazo de control de Oxígeno Disuelto (RAS) — PID", fontsize=13)

ax_y = fig.add_axes([0.08, 0.74, 0.62, 0.20])
ax_e = fig.add_axes([0.08, 0.55, 0.62, 0.15])
ax_d = fig.add_axes([0.08, 0.36, 0.62, 0.15])
ax_u = fig.add_axes([0.08, 0.17, 0.62, 0.15])

# --- y(t): Respuesta ---
ax_y.set_ylabel("y(t) [mg/L]")
ax_y.grid(True, alpha=0.3)
ax_y.set_title("Respuesta (Oxígeno Disuelto)", fontsize=9, loc="left")
line_y, = ax_y.plot([], [], color="#0d6efd", lw=1.8, label="y(t) medido")
line_r, = ax_y.plot([], [], color="#dc3545", lw=1.1, ls="--", label="r(t) set-point")
line_umb_inf = ax_y.axhline(params["umbral_inf"], color="#ffc107", lw=1.2, ls=":", label="umbral falla")
line_umb_sup = ax_y.axhline(params["umbral_sup"], color="#ffc107", lw=1.2, ls=":")
banda_falla = ax_y.axhspan(params["umbral_inf"], params["umbral_sup"], color="#198754", alpha=0.06)
ax_y.legend(loc="upper right", fontsize=7)
ax_y.set_ylim(2, 12)

# --- e(t): Error ---
ax_e.set_ylabel("e(t) [mg/L]")
ax_e.grid(True, alpha=0.3)
ax_e.set_title("Señal de error e(t) = r(t) - y(t)", fontsize=9, loc="left")
ax_e.axhline(0, color="gray", lw=0.8)
line_e, = ax_e.plot([], [], color="#6f42c1", lw=1.5)
ax_e.set_ylim(-4, 4)

# --- d(t): Perturbación ---
ax_d.set_ylabel("d(t) [mg/L/s]")
ax_d.grid(True, alpha=0.3)
ax_d.set_title("Perturbación d(t) (biomasa / alimentación / temperatura)", fontsize=9, loc="left")
ax_d.axhline(0, color="gray", lw=0.8)
line_d, = ax_d.plot([], [], color="#fd7e14", lw=1.5)
ax_d.set_ylim(-0.03, 0.03)

# --- u(t): Señal de entrada ---
ax_u.set_ylabel("u(t) [Hz]")
ax_u.set_xlabel("tiempo [s]")
ax_u.grid(True, alpha=0.3)
ax_u.set_title("Señal de entrada u(t) (frecuencia aplicada al variador)", fontsize=9, loc="left")
line_u, = ax_u.plot([], [], color="#198754", lw=1.5)
ax_u.set_ylim(U_MIN - 2, U_MAX + 2)

texto_estado = fig.text(0.08, 0.965, "", fontsize=10, family="monospace")

# ------------------------------------------------------------------
# Sliders (columna derecha)
# ------------------------------------------------------------------
def _slider_axis(y):
    return fig.add_axes([0.76, y, 0.20, 0.022])

fig.text(0.76, 0.955, "Parámetros del PID", fontsize=9, weight="bold")
s_kp = Slider(_slider_axis(0.925), "Kp", 0.0, 10.0, valinit=params["kp"])
s_ki = Slider(_slider_axis(0.885), "Ki", 0.0, 0.10, valinit=params["ki"])
s_kd = Slider(_slider_axis(0.845), "Kd", 0.0, 50.0, valinit=params["kd"])

fig.text(0.76, 0.815, "Referencia", fontsize=9, weight="bold")
s_sp = Slider(_slider_axis(0.785), "Set-point r", 5.0, 9.0, valinit=params["setpoint"])

fig.text(0.76, 0.755, "Perturbación", fontsize=9, weight="bold")
s_amp = Slider(_slider_axis(0.725), "Amplitud [mg/L]", -3.0, 3.0, valinit=params["pert_amp"])
s_dur = Slider(_slider_axis(0.685), "Duración [s]", 5.0, 600.0, valinit=params["pert_dur"])

fig.text(0.76, 0.645, "Umbrales de falla", fontsize=9, weight="bold")
s_uinf = Slider(_slider_axis(0.615), "Umbral inf.", 3.0, 7.0, valinit=params["umbral_inf"])
s_usup = Slider(_slider_axis(0.575), "Umbral sup.", 7.0, 11.0, valinit=params["umbral_sup"])


def _actualizar_kp(v): params["kp"] = v
def _actualizar_ki(v): params["ki"] = v
def _actualizar_kd(v): params["kd"] = v
def _actualizar_sp(v): params["setpoint"] = v
def _actualizar_amp(v): params["pert_amp"] = v
def _actualizar_dur(v): params["pert_dur"] = v


def _actualizar_uinf(v):
    params["umbral_inf"] = v
    line_umb_inf.set_ydata([v, v])
    _redibujar_banda()


def _actualizar_usup(v):
    params["umbral_sup"] = v
    line_umb_sup.set_ydata([v, v])
    _redibujar_banda()


def _redibujar_banda():
    global banda_falla
    banda_falla.remove()
    banda_falla = ax_y.axhspan(params["umbral_inf"], params["umbral_sup"], color="#198754", alpha=0.06)


s_kp.on_changed(_actualizar_kp)
s_ki.on_changed(_actualizar_ki)
s_kd.on_changed(_actualizar_kd)
s_sp.on_changed(_actualizar_sp)
s_amp.on_changed(_actualizar_amp)
s_dur.on_changed(_actualizar_dur)
s_uinf.on_changed(_actualizar_uinf)
s_usup.on_changed(_actualizar_usup)

# ------------------------------------------------------------------
# Botones
# ------------------------------------------------------------------
ax_play = fig.add_axes([0.76, 0.48, 0.09, 0.045])
ax_reset = fig.add_axes([0.87, 0.48, 0.09, 0.045])
ax_pert = fig.add_axes([0.76, 0.42, 0.20, 0.045])

b_play = Button(ax_play, "Play")
b_reset = Button(ax_reset, "Reset")
b_pert = Button(ax_pert, "Aplicar perturbación")


def _toggle_play(event):
    playing["on"] = not playing["on"]
    b_play.label.set_text("Pausa" if playing["on"] else "Play")


def _reset(event):
    sim.reset()
    playing["on"] = False
    b_play.label.set_text("Play")


def _aplicar_perturbacion(event):
    sim.disparar_perturbacion(params["pert_amp"], params["pert_dur"])


b_play.on_clicked(_toggle_play)
b_reset.on_clicked(_reset)
b_pert.on_clicked(_aplicar_perturbacion)

# ------------------------------------------------------------------
# Loop de animación
# ------------------------------------------------------------------
def _update(frame):
    if playing["on"]:
        pasos = max(1, int(SIM_SECONDS_PER_FRAME / DT_SIM))
        for _ in range(pasos):
            sim.paso(
                params["kp"], params["ki"], params["kd"], params["setpoint"],
                params["umbral_inf"], params["umbral_sup"],
            )

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

    y_now = sim.hist_y[-1] if sim.hist_y else C0_LIN
    e_now = sim.hist_e[-1] if sim.hist_e else 0.0
    u_now = sim.hist_u[-1] if sim.hist_u else U0
    d_now = sim.hist_d[-1] if sim.hist_d else 0.0

    if sim.en_falla:
        estado = "⚠ FALLA (fuera de umbral)"
        color_estado = "#dc3545"
        line_y.set_color("#dc3545")
    else:
        estado = "NORMAL (dentro de banda tolerada)"
        color_estado = "#198754"
        line_y.set_color("#0d6efd")

    texto_estado.set_text(
        f"t={sim.t:7.1f}s  y={y_now:5.2f}mg/L  e={e_now:+5.2f}mg/L  "
        f"u={u_now:5.1f}Hz  d={d_now:+.4f}mg/L·s⁻¹   |   Estado: {estado}"
    )
    texto_estado.set_color(color_estado)

    return line_y, line_r, line_e, line_d, line_u, texto_estado


anim = FuncAnimation(fig, _update, interval=FRAME_INTERVAL_MS, blit=False, cache_frame_data=False)

if __name__ == "__main__":
    plt.show()
