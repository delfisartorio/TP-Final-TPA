import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button, TextBox

# --- 1. CONFIGURACIÓN Y PARÁMETROS INICIALES ---
Kp, Ti, setpoint = 2.5, 180.0, 7.0
Kp_planta, tau = 0.08, 300
dt = 0.5 

# Estado
y, integral, t = 6.0, 0, 0
data = {'t': [], 'y': [], 'u': [], 'r': []}
perturbacion_activa = 0
tiempo_restante_perturbacion = 0

# --- 2. BLOQUES FUNCIONALES (MODELADO) ---
def bloque_controlador_pi(error, integral):
    """Calcula la acción de control u(t) con anti-windup [cite: 117, 123]"""
    p = Kp * error
    integral += (Kp / Ti) * error * dt
    u_out = np.clip(p + integral, 0, 50) # Salida limitada 0-50Hz [cite: 106, 139]
    return u_out, integral

def bloque_proceso_ras(u, y, perturbacion):
    """Física del proceso: Balance de masa [cite: 148, 150]"""
    derivada = (-(y - 7.0) + Kp_planta * (u - perturbacion)) / tau
    return y + derivada * dt

# --- 3. INTERFAZ GRÁFICA ---
fig, (ax_main, ax_ctrl) = plt.subplots(2, 1, figsize=(10, 8))
plt.subplots_adjust(bottom=0.35)

line_y, = ax_main.plot([], [], label='Oxígeno Real y(t)')
line_r, = ax_main.plot([], [], '--', label='Set-point r(t)')
ax_main.fill_between([], [], color='red', alpha=0.1, label='Banda de Error')
ax_main.set_ylim(0, 10); ax_main.set_xlim(0, 300); ax_main.legend()

line_u, = ax_ctrl.plot([], [], color='orange', label='Salida Aireador u(t) [Hz]')
ax_ctrl.set_ylim(0, 55); ax_ctrl.set_xlim(0, 300); ax_ctrl.legend()

# --- 4. CONTROLES DE USUARIO ---
ax_kp = plt.axes([0.15, 0.25, 0.3, 0.03]); s_kp = Slider(ax_kp, 'Kp', 0.1, 10.0, valinit=Kp)
ax_amp = plt.axes([0.6, 0.25, 0.3, 0.03]); s_amp = Slider(ax_amp, 'Amplitud Pert.', 0.0, 3.0, valinit=1.5)
ax_dur = plt.axes([0.6, 0.2, 0.3, 0.03]); s_dur = Slider(ax_dur, 'Duración (s)', 10, 120, valinit=30)

def trigger_perturbacion(event):
    global perturbacion_activa, tiempo_restante_perturbacion
    perturbacion_activa = s_amp.val
    tiempo_restante_perturbacion = s_dur.val

btn_ax = plt.axes([0.3, 0.05, 0.4, 0.08])
btn = Button(btn_ax, 'APLICAR PERTURBACIÓN (Alimentación)')
btn.on_clicked(trigger_perturbacion)

# --- 5. LÓGICA DINÁMICA ---
def update(frame):
    global y, integral, t, perturbacion_activa, tiempo_restante_perturbacion
    error = setpoint - y
    u, integral = bloque_controlador_pi(error, integral)
    
    # Aplicar perturbación si hay tiempo restante
    carga = perturbacion_activa if tiempo_restante_perturbacion > 0 else 0
    y = bloque_proceso_ras(u, y, carga)
    
    if tiempo_restante_perturbacion > 0: tiempo_restante_perturbacion -= dt
    
    t += dt
    data['t'].append(t); data['y'].append(y); data['u'].append(u)
    
    line_y.set_data(data['t'], data['y'])
    line_r.set_data(data['t'], [setpoint]*len(data['t']))
    line_u.set_data(data['t'], data['u'])
    
    if t > 300: ax_main.set_xlim(t-300, t+50); ax_ctrl.set_xlim(t-300, t+50)
    return line_y, line_u

ani = FuncAnimation(fig, update, interval=50, blit=True)
plt.show()