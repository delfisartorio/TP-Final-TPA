import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button

# --- CONFIGURACIÓN SEGÚN INFORME DE LA UTN (PÁG 12) ---
K_planta = 0.08    # Ganancia estática linealizada (mg/L)/Hz
tau = 180.0        # Constante de tiempo del estanque (3 minutos)
dt = 4.0           # ¡MÁS RÁPIDO! Avanza 4 segundos de proceso por cada cuadro de animación

# Puntos de operación del diseño (Bias)
u_operacion = 30.0  # Hz nominales
y_operacion = 7.0   # mg/L nominales (Set-point fijo)

set_point = 7.0    
banda_error = 0.3  

# Sintonía inicial del PI (Robusta para el punto de operación)
Kp_actual = 3.5    
Ki_actual = 0.025  

# Vectores de datos
t_data, r_data, y_data, e_data, u_data, d_data = [], [], [], [], [], []
integral = 0.0
tiempo_actual = 0.0

# Perturbación interactiva (Consumo por alimentación)
importante_antirebote = False
perturbacion_activa = False
tiempo_inicio_perturbacion = 0.0
pert_amplitud = 1.5    
pert_duracion = 90.0   

# --- CONFIGURACIÓN GRÁFICA ---
fig, axs = plt.subplots(4, 1, figsize=(11, 8.5), sharex=True)
plt.subplots_adjust(hspace=0.4, bottom=0.25, right=0.95, top=0.93)
fig.canvas.manager.set_window_title('UTN.BA - Simulación Corregida por Punto de Operación')

line_y, = axs[0].plot([], [], 'b-', label='OD Real y(t)', linewidth=2)
line_r, = axs[0].plot([], [], 'r--', label='Set-point r(t) (Fijo 7 mg/L)', linewidth=1.5)
line_e, = axs[1].plot([], [], 'g-', label='Error e(t)', linewidth=2)
line_u, = axs[2].plot([], [], 'm-', label='Salida Control u(t) (Variador Siemens)', linewidth=1.5)
line_d, = axs[3].plot([], [], 'k-', label='Perturbación d(t) (Consumo Biomasa)', linewidth=1.5)

# Límites corregidos para que NADA se oculte de la pantalla
axs[0].set_ylabel('OD (mg/L)')
axs[0].set_title('Simulación Interactiva en Tiempo Real (Física de Desviación Correcta)')
axs[0].legend(loc='upper right')
axs[0].set_ylim(2, 10)

axs[1].set_ylabel('Error (mg/L)')
axs[1].axhline(0, color='black', linestyle='-', linewidth=0.5)
axs[1].axhline(banda_error, color='red', linestyle=':', alpha=0.7, label='Umbral Máx Tolerancia')
axs[1].axhline(-banda_error, color='red', linestyle=':', alpha=0.7)
axs[1].legend(loc='upper right')
axs[1].set_ylim(-2.5, 2.5) # Escala ampliada para ver el transitorio inicial

axs[2].set_ylabel('Soplador (Hz)')
axs[2].legend(loc='upper right')
axs[2].set_ylim(-5, 55)

axs[3].set_ylabel('Demanda (mg/L)')
axs[3].set_xlabel('Tiempo (segundos)')
axs[3].legend(loc='upper right')
axs[3].set_ylim(-0.5, 3.5)

for ax in axs:
    ax.grid(True)
    ax.set_xlim(0, 500)

# Condición inicial: El estanque arranca con un déficit real en 4.0 mg/L
y_actual = 4.0

# --- BUCLE DE SIMULACIÓN CON VARIABLES DE DESVIACIÓN ---
def actualizar_simulacion(frame):
    global tiempo_actual, y_actual, integral, perturbacion_activa, tiempo_inicio_perturbacion
    
    # 1. Manejo de perturbación por pulso
    d_actual = 0.0
    if perturbacion_activa:
        if tiempo_actual - tiempo_inicio_perturbacion <= pert_duracion:
            d_actual = pert_amplitud
        else:
            perturbacion_activa = False 
            
    # 2. Señal de error absoluta (r - y)
    e_actual = set_point - y_actual
    
    # 3. Algoritmo del Controlador PI
    proporcional = Kp_actual * e_actual
    PI_calculado = proporcional + Ki_actual * (integral + e_actual * dt)
    
    # Anti-windup acoplado a la saturación del variador Siemens (0-50 Hz)
    if 0.0 <= PI_calculado <= 50.0:
        integral += e_actual * dt
        
    u_actual = proporcional + Ki_actual * integral
    u_actual = np.clip(u_actual, 0.0, 50.0)
    
    # 4. FÍSICA CORRECTA: Ecuación diferencial con variables de desviación
    delta_u = u_actual - u_operacion  # Cuánto se aleja el soplador de los 30Hz nominales
    delta_y = y_actual - y_operacion   # Cuánto se aleja el OD de los 7mg/L nominales
    
    # El diferencial calcula la evolución basándose en el punto de equilibrio linealizado
    dy = ((K_planta * delta_u) - delta_y - d_actual) * (dt / tau)
    y_actual += dy
    
    # Guardar datos
    tiempo_actual += dt
    t_data.append(tiempo_actual)
    r_data.append(set_point)
    y_data.append(y_actual)
    e_data.append(e_actual)
    u_data.append(u_actual)
    d_data.append(d_actual)
    
    if tiempo_actual > 500:
        for ax in axs:
            ax.set_xlim(tiempo_actual - 500, tiempo_actual)
            
    # Mapear curvas
    line_y.set_data(t_data, y_data)
    line_r.set_data(t_data, r_data)
    line_e.set_data(t_data, e_data)
    line_u.set_data(t_data, u_data)
    line_d.set_data(t_data, d_data)
    
    return line_y, line_r, line_e, line_u, line_d

# --- PANEL DE CONTROLES DESLIZANTES ---
ax_kp = plt.axes([0.15, 0.14, 0.25, 0.03])
ax_ki = plt.axes([0.15, 0.08, 0.25, 0.03])
ax_p_amp = plt.axes([0.65, 0.14, 0.25, 0.03])
ax_p_dur = plt.axes([0.65, 0.08, 0.25, 0.03])
ax_btn_pert = plt.axes([0.43, 0.01, 0.20, 0.04])

slider_kp = Slider(ax_kp, 'Ganancia Kp', 0.5, 15.0, valinit=Kp_actual, valfmt='%1.1f')
slider_ki = Slider(ax_ki, 'Ganancia Ki', 0.001, 0.1, valinit=Ki_actual, valfmt='%1.3f')
slider_p_amp = Slider(ax_p_amp, 'Amp. Perturbación', 0.0, 3.0, valinit=pert_amplitud, valfmt='%1.1f mg/L')
slider_p_dur = Slider(ax_p_dur, 'Duración Pulso (s)', 10.0, 200.0, valinit=pert_duracion, valfmt='%1.0f s')
btn_pert = Button(ax_btn_pert, 'DISPARAR PERTURBACIÓN', color='crimson', hovercolor='darkred')

def actualizar_kp(val): global Kp_actual; Kp_actual = val
def actualizar_ki(val): global Ki_actual; Ki_actual = val
def actualizar_p_amp(val): global pert_amplitud; pert_amplitud = val
def actualizar_p_dur(val): global pert_duracion; pert_duracion = val

def aplicar_carga(event):
    global perturbacion_activa, tiempo_inicio_perturbacion
    if not perturbacion_activa:
        perturbacion_activa = True
        tiempo_inicio_perturbacion = tiempo_actual

slider_kp.on_changed(actualizar_kp)
slider_ki.on_changed(actualizar_ki)
slider_p_amp.on_changed(actualizar_p_amp)
slider_p_dur.on_changed(actualizar_p_dur)
btn_pert.on_clicked(aplicar_carga)

ani = FuncAnimation(fig, actualizar_simulacion, blit=True, interval=20, cache_frame_data=False)
plt.show()