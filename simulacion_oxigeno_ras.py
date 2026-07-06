import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button

# --- CONFIGURACIÓN SEGÚN INFORME UTN (PÁG 12) ---
K_planta = 0.08    # Ganancia estática linealizada (mg/L)/Hz
tau = 180.0        # Constante de tiempo del estanque (3 minutos = 180s)
dt = 0.9           # Avance de tiempo suavizado por cuadro

# Puntos de operación nominales dinámicos
u_operacion = 30.0  # Hz nominales
set_point = 7.0     # Inicialmente en 7.0
y_operacion = set_point 

banda_error = 0.8  

# Sintonía inicial fiel al comportamiento real del proceso
Kp_actual = 3.0    
Ki_actual = 0.012  

# Vectores de datos
t_data, r_data, y_data, e_data, u_data, d_data = [], [], [], [], [], []
integral = 0.0
tiempo_actual = 0.0

# Variables de perturbación y estado de la animación
perturbacion_activa = False
tiempo_inicio_perturbacion = 0.0
pert_amplitud = 2.0    
pert_duracion = 120.0  
simulacion_en_pausa = False

# --- CONFIGURACIÓN GRÁFICA ---
fig, axs = plt.subplots(4, 1, figsize=(11, 8.5), sharex=True)
plt.subplots_adjust(hspace=0.4, bottom=0.28, right=0.95, top=0.93)
fig.canvas.manager.set_window_title('UTN.BA - Simulación Interactiva')

line_y, = axs[0].plot([], [], 'b-', label='OD Real y(t)', linewidth=2)
line_r, = axs[0].plot([], [], 'r--', label='Set-point r(t)', linewidth=1.5)
line_e, = axs[1].plot([], [], 'g-', label='Error e(t)', linewidth=2)
line_u, = axs[2].plot([], [], 'm-', label='Salida Control u(t) (Variador Siemens)', linewidth=1.5)
line_d, = axs[3].plot([], [], 'k-', label='Perturbación d(t) (Consumo Biomasa)', linewidth=1.5)

# Configuración de límites fijos óptimos
axs[0].set_ylabel('OD (mg/L)')
axs[0].set_title('Simulación Interactiva - Control de Oxígeno en RAS (Tiempo Real Con Pausa)')
axs[0].legend(loc='upper right')
axs[0].set_ylim(1.5, 9.5)

axs[1].set_ylabel('Error (mg/L)')
axs[1].axhline(0, color='black', linestyle='-', linewidth=0.5)
axs[1].axhline(banda_error, color='red', linestyle=':', alpha=0.7, label='Umbral Máx Tolerancia')
axs[1].axhline(-banda_error, color='red', linestyle=':', alpha=0.7)
axs[1].legend(loc='upper right')
axs[1].set_ylim(-3.0, 3.0) 

axs[2].set_ylabel('Soplador (Hz)')
axs[2].legend(loc='upper right')
axs[2].set_ylim(-5, 55)

axs[3].set_ylabel('Demanda (mg/L)')
axs[3].set_xlabel('Tiempo (segundos)')
axs[3].legend(loc='upper right')
axs[3].set_ylim(-0.5, 4.5)

for ax in axs:
    ax.grid(True)
    ax.set_xlim(0, 400)

# Condición inicial
y_actual = 0.0

# --- BUCLE DE SIMULACIÓN DINÁMICA ---
def actualizar_simulacion(frame):
    global tiempo_actual, y_actual, integral, perturbacion_activa, tiempo_inicio_perturbacion
    
    if simulacion_en_pausa:
        return line_y, line_r, line_e, line_u, line_d
        
    # 1. Manejo dinámico de la perturbación por pulso
    d_actual = 0.0
    if perturbacion_activa:
        if tiempo_actual - tiempo_inicio_perturbacion <= pert_duracion:
            d_actual = pert_amplitud
        else:
            perturbacion_activa = False 
            
    # 2. Señal de error absoluta (r - y)
    e_actual = set_point - y_actual
    
    # 3. Algoritmo del Controlador PI con Anti-Windup y Bias de Operación
    proporcional = Kp_actual * e_actual
    PI_calculado = proporcional + Ki_actual * (integral + e_actual * dt) + u_operacion
    
    if 0.0 <= PI_calculado <= 50.0:
        integral += e_actual * dt
        
    u_actual = proporcional + Ki_actual * integral + u_operacion
    u_actual = np.clip(u_actual, 0.0, 50.0)
    
    # 4. Física de Desviación con acoplamiento temporal amortiguado
    delta_u = u_actual - u_operacion  
    delta_y = y_actual - y_operacion   
    
    dy = ((K_planta * delta_u) - delta_y - d_actual) * (dt / tau)
    y_actual += dy
    
    # Guardar datos en los vectores históricos
    tiempo_actual += dt
    t_data.append(tiempo_actual)
    r_data.append(set_point)
    y_data.append(y_actual)
    e_data.append(e_actual)
    u_data.append(u_actual)
    d_data.append(d_actual)
    
    # Eje X móvil (Ventana de 400 segundos)
    if tiempo_actual > 400:
        for ax in axs:
            ax.set_xlim(tiempo_actual - 400, tiempo_actual)
            
    # Renderizar curvas
    line_y.set_data(t_data, y_data)
    line_r.set_data(t_data, r_data)
    line_e.set_data(t_data, e_data)
    line_u.set_data(t_data, u_data)
    line_d.set_data(t_data, d_data)
    
    return line_y, line_r, line_e, line_u, line_d

# --- PANEL DE CONTROLES ---
ax_sp    = plt.axes([0.15, 0.19, 0.25, 0.025])
ax_kp    = plt.axes([0.15, 0.14, 0.25, 0.025])
ax_ki    = plt.axes([0.15, 0.09, 0.25, 0.025])

ax_p_amp = plt.axes([0.65, 0.16, 0.25, 0.025])
ax_p_dur = plt.axes([0.65, 0.11, 0.25, 0.025])

ax_btn_pert  = plt.axes([0.18, 0.02, 0.18, 0.04])
ax_btn_pausa = plt.axes([0.41, 0.02, 0.18, 0.04])
ax_btn_reset = plt.axes([0.64, 0.02, 0.18, 0.04])

# CAMBIO AQUÍ: Rango modificado estrictamente entre 6.0 y 8.0
slider_sp    = Slider(ax_sp, 'Set-point (r)', 6.0, 8.0, valinit=set_point, valfmt='%1.1f mg/L')
slider_kp    = Slider(ax_kp, 'Ganancia Kp', 0.5, 15.0, valinit=Kp_actual, valfmt='%1.1f')
slider_ki    = Slider(ax_ki, 'Ganancia Ki', 0.001, 0.1, valinit=Ki_actual, valfmt='%1.3f')
slider_p_amp = Slider(ax_p_amp, 'Amp. Perturbación', 0.0, 4.0, valinit=pert_amplitud, valfmt='%1.1f mg/L')
slider_p_dur = Slider(ax_p_dur, 'Duración Pulso (s)', 10.0, 300.0, valinit=pert_duracion, valfmt='%1.0f s')

btn_pert  = Button(ax_btn_pert, 'DISPARAR PERTURBACIÓN', color='crimson', hovercolor='darkred')
btn_pausa = Button(ax_btn_pausa, 'PAUSAR SISTEMA', color='gold', hovercolor='orange')
btn_reset = Button(ax_btn_reset, 'REINICIAR', color='skyblue', hovercolor='deepskyblue')

# Callbacks
def actualizar_sp(val):
    global set_point, y_operacion
    set_point = val
    y_operacion = val  

def actualizar_kp(val): global Kp_actual; Kp_actual = val
def actualizar_ki(val): global Ki_actual; Ki_actual = val
def actualizar_p_amp(val): global pert_amplitud; pert_amplitud = val
def actualizar_p_dur(val): global pert_duracion; pert_duracion = val

def aplicar_carga(event):
    global perturbacion_activa, tiempo_inicio_perturbacion
    if not perturbacion_activa and not simulacion_en_pausa:
        perturbacion_activa = True
        tiempo_inicio_perturbacion = tiempo_actual

def alternar_pausa(event):
    global simulacion_en_pausa
    simulacion_en_pausa = not simulacion_en_pausa
    if simulacion_en_pausa:
        btn_pausa.label.set_text('REANUDAR SISTEMA')
        btn_pausa.color = 'limegreen'
        btn_pausa.hovercolor = 'darkgreen'
    else:
        btn_pausa.label.set_text('PAUSAR SISTEMA')
        btn_pausa.color = 'gold'
        btn_pausa.hovercolor = 'orange'
    fig.canvas.draw_idle()

# --- FUNCIÓN DE REINICIO CORREGIDA ---
def reiniciar_simulacion(event):
    global t_data, r_data, y_data, e_data, u_data, d_data, integral, tiempo_actual, y_actual, perturbacion_activa, simulacion_en_pausa, set_point, y_operacion
    
    # 1. Vaciar listas de datos históricos
    t_data.clear()
    r_data.clear()
    y_data.clear()
    e_data.clear()
    u_data.clear()
    d_data.clear()
    
    # 2. Forzar el vaciado visual de las curvas para eliminar las líneas "fantasma"
    line_y.set_data([], [])
    line_r.set_data([], [])
    line_e.set_data([], [])
    line_u.set_data([], [])
    line_d.set_data([], [])
    
    # 3. Resetear variables de estado al valor actual del Slider
    integral = 0.0
    tiempo_actual = 0.0
    set_point = slider_sp.val
    y_operacion = set_point
    y_actual = 0.0
    
    perturbacion_activa = False
    simulacion_en_pausa = False
    
    # 4. Reajustar botones e interfaz
    btn_pausa.label.set_text('PAUSAR SISTEMA')
    btn_pausa.color = 'gold'
    btn_pausa.hovercolor = 'orange'
    
    for ax in axs: 
        ax.set_xlim(0, 400)
        
    # 5. Redibujar el lienzo completamente limpio
    fig.canvas.draw_idle()

slider_sp.on_changed(actualizar_sp)
slider_kp.on_changed(actualizar_kp)
slider_ki.on_changed(actualizar_ki)
slider_p_amp.on_changed(actualizar_p_amp)
slider_p_dur.on_changed(actualizar_p_dur)
btn_pert.on_clicked(aplicar_carga)
btn_pausa.on_clicked(alternar_pausa)
btn_reset.on_clicked(reiniciar_simulacion)

ani = FuncAnimation(fig, actualizar_simulacion, blit=True, interval=30, cache_frame_data=False)
plt.show()