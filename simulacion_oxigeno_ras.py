import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button

# ============================================================================
# BLOQUE 1: PARÁMETROS DE LA PLANTA (el estanque de cultivo - RAS)
# ============================================================================
# Modelo FOPDT (Primer Orden) linealizado alrededor del punto de operación.
# Relaciona el Hz del soplador con el oxígeno disuelto (OD) resultante.
K_planta = 0.08    # Ganancia estática: cuánto sube el OD (mg/L) por cada Hz de más
tau = 180.0        # Constante de tiempo del estanque (3 minutos = 180 s):
                    # qué tan rápido reacciona el agua a un cambio de aireación

u_operacion = 30.0  # Punto de operación nominal del soplador (Hz)
set_point = 7.0      # Consigna inicial de OD deseado (mg/L)
y_operacion = set_point  # OD correspondiente al punto de operación

dt = 0.9  # Paso de tiempo simulado por cuadro de animación (segundos)


# ============================================================================
# BLOQUE 2: PARÁMETROS DEL CONTROLADOR PI
# ============================================================================
Kp_actual = 7.5     # Ganancia proporcional: reacción inmediata al error
Ki_actual = 0.091   # Ganancia integral: corrige el error acumulado en el tiempo
banda_error = 0.8   # Umbral de tolerancia (mg/L) que se marca en el gráfico de error


# ============================================================================
# BLOQUE 3: PARÁMETROS DE LA PERTURBACIÓN (consumo de oxígeno de la biomasa)
# ============================================================================
perturbacion_activa = False
tiempo_inicio_perturbacion = 0.0
pert_amplitud = 1.6     # Magnitud de la perturbación (mg/L de OD consumido)
pert_duracion = 4000.0  # Duración del pulso de perturbación (segundos)


# ============================================================================
# BLOQUE 4: ESTADO DE LA SIMULACIÓN
# ============================================================================
t_data, r_data, y_data, e_data, u_data, d_data = [], [], [], [], [], []
integral = 0.0        # Acumulador del término integral del PI
tiempo_actual = 0.0
y_actual = 0.0         # Oxígeno disuelto actual (variable controlada)
simulacion_en_pausa = False

VENTANA = 400.0   # Ancho de la ventana de tiempo visible en el gráfico (s)
pagina_actual = 0  # Índice de la ventana de tiempo actualmente en pantalla


# ============================================================================
# BLOQUE 5: FUNCIONES DEL LAZO DE CONTROL
# ============================================================================
# Cada función representa un bloque del diagrama de control clásico:
# Perturbación -> Sensor/Error -> Controlador -> Actuador/Planta -> (realimentación)

def calcular_perturbacion():
    """Bloque PERTURBACIÓN: devuelve la demanda de oxígeno de la biomasa
    mientras el pulso disparado por el usuario esté activo."""
    global perturbacion_activa
    if not perturbacion_activa:
        return 0.0
    if tiempo_actual - tiempo_inicio_perturbacion <= pert_duracion:
        return pert_amplitud
    perturbacion_activa = False
    return 0.0


def calcular_error(consigna, medicion):
    """Bloque SENSOR/COMPARADOR: error entre lo que se quiere (set-point)
    y lo que se mide realmente (OD actual)."""
    return consigna - medicion


def controlador_PI(e_actual):
    """Bloque CONTROLADOR PI: convierte el error en una orden para el
    actuador (frecuencia del soplador), con anti-windup para no saturar
    el término integral cuando la salida ya está en su límite físico."""
    global integral

    proporcional = Kp_actual * e_actual
    salida_tentativa = proporcional + Ki_actual * (integral + e_actual * dt) + u_operacion

    # Anti-windup: solo se acumula el error en la integral si la salida
    # resultante no se va a saturar (queda dentro del rango físico del soplador)
    if 0.0 <= salida_tentativa <= 50.0:
        integral += e_actual * dt

    u_calculado = proporcional + Ki_actual * integral + u_operacion
    return np.clip(u_calculado, 0.0, 50.0)  # Bloque ACTUADOR: límites físicos del variador (0-50 Hz)


def modelo_planta(u_actual, d_actual, y_previo):
    """Bloque PLANTA: dinámica física del estanque. Traduce la acción del
    actuador (Hz) y la perturbación (consumo de biomasa) en la evolución
    real del oxígeno disuelto, con la inercia térmica/física dada por tau."""
    delta_u = u_actual - u_operacion
    delta_y = y_previo - y_operacion
    dy = ((K_planta * delta_u) - delta_y - d_actual) * (dt / tau)
    return y_previo + dy


# ============================================================================
# BLOQUE 6: CONFIGURACIÓN GRÁFICA (visualización del lazo)
# ============================================================================
fig, axs = plt.subplots(4, 1, figsize=(11, 8.5), sharex=True)
plt.subplots_adjust(hspace=0.4, bottom=0.28, right=0.95, top=0.93)
fig.canvas.manager.set_window_title('UTN.BA - Simulación Interactiva')

line_y, = axs[0].plot([], [], 'b-', label='OD Real y(t)', linewidth=2)
line_r, = axs[0].plot([], [], 'r--', label='Set-point r(t)', linewidth=1.5)
line_e, = axs[1].plot([], [], 'g-', label='Error e(t)', linewidth=2)
line_u, = axs[2].plot([], [], 'm-', label='Salida Control u(t) (Variador Siemens)', linewidth=1.5)
line_d, = axs[3].plot([], [], 'k-', label='Perturbación d(t) (Consumo Biomasa)', linewidth=1.5)

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
axs[2].set_ylim(-5, 55)

axs[3].set_ylabel('Demanda (mg/L)')
axs[3].set_xlabel('Tiempo (segundos)')
axs[3].legend(loc='upper right')
axs[3].set_ylim(-0.5, 4.5)

for ax in axs:
    ax.grid(True)
    ax.set_xlim(0, VENTANA)


# ============================================================================
# BLOQUE 7: BUCLE PRINCIPAL DE SIMULACIÓN (orquesta todos los bloques)
# ============================================================================
def actualizar_simulacion(frame):
    global tiempo_actual, y_actual, pagina_actual

    if simulacion_en_pausa:
        return line_y, line_r, line_e, line_u, line_d

    # 1. PERTURBACIÓN: cuánto oxígeno está consumiendo la biomasa ahora mismo
    d_actual = calcular_perturbacion()

    # 2. SENSOR/ERROR: comparar lo medido contra la consigna
    e_actual = calcular_error(set_point, y_actual)

    # 3. CONTROLADOR + ACTUADOR: calcular la orden para el soplador
    u_actual = controlador_PI(e_actual)

    # 4. PLANTA: aplicar esa orden (y la perturbación) al estanque real
    y_actual = modelo_planta(u_actual, d_actual, y_actual)

    # 5. Registrar el nuevo instante en el historial (para graficar)
    tiempo_actual += dt
    t_data.append(tiempo_actual)
    r_data.append(set_point)
    y_data.append(y_actual)
    e_data.append(e_actual)
    u_data.append(u_actual)
    d_data.append(d_actual)

    # 6. EJE X PAGINADO: cuando la curva llega al borde de la pantalla,
    # se avanza a la siguiente "página" de tiempo (0-400, 400-800, ...).
    # Esto deja claro que el salto ocurre porque el tiempo avanzó, y al
    # recalcular el eje solo de vez en cuando (no en cada cuadro) se
    # mantiene la velocidad rápida del blitting.
    nueva_pagina = int(tiempo_actual // VENTANA)
    if nueva_pagina != pagina_actual:
        pagina_actual = nueva_pagina
        inicio = pagina_actual * VENTANA
        for ax in axs:
            ax.set_xlim(inicio, inicio + VENTANA)
        fig.canvas.draw()  # redibujo completo puntual para refrescar el fondo del blit

    # 7. Renderizar curvas
    line_y.set_data(t_data, y_data)
    line_r.set_data(t_data, r_data)
    line_e.set_data(t_data, e_data)
    line_u.set_data(t_data, u_data)
    line_d.set_data(t_data, d_data)

    return line_y, line_r, line_e, line_u, line_d


# ============================================================================
# BLOQUE 8: PANEL DE CONTROLES (sliders y botones)
# ============================================================================
ax_sp    = plt.axes([0.15, 0.19, 0.25, 0.025])
ax_kp    = plt.axes([0.15, 0.14, 0.25, 0.025])
ax_ki    = plt.axes([0.15, 0.09, 0.25, 0.025])

ax_p_amp = plt.axes([0.65, 0.16, 0.25, 0.025])
ax_p_dur = plt.axes([0.65, 0.11, 0.25, 0.025])

ax_btn_pert  = plt.axes([0.18, 0.02, 0.18, 0.04])
ax_btn_pausa = plt.axes([0.41, 0.02, 0.18, 0.04])
ax_btn_reset = plt.axes([0.64, 0.02, 0.18, 0.04])

slider_sp    = Slider(ax_sp, 'Set-point (r)', 6.0, 8.0, valinit=set_point, valfmt='%1.1f mg/L')
slider_kp    = Slider(ax_kp, 'Ganancia Kp', 0.5, 15.0, valinit=Kp_actual, valfmt='%1.1f')
slider_ki    = Slider(ax_ki, 'Ganancia Ki', 0.001, 0.1, valinit=Ki_actual, valfmt='%1.3f')
slider_p_amp = Slider(ax_p_amp, 'Amp. Perturbación', 0.0, 4.0, valinit=pert_amplitud, valfmt='%1.1f mg/L')
slider_p_dur = Slider(ax_p_dur, 'Duración Pulso (s)', 10.0, 4000.0, valinit=pert_duracion, valfmt='%1.0f s')

btn_pert  = Button(ax_btn_pert, 'DISPARAR PERTURBACIÓN', color='crimson', hovercolor='darkred')
btn_pausa = Button(ax_btn_pausa, 'PAUSAR SISTEMA', color='gold', hovercolor='orange')
btn_reset = Button(ax_btn_reset, 'REINICIAR', color='skyblue', hovercolor='deepskyblue')


# ============================================================================
# BLOQUE 9: CALLBACKS DE LA INTERFAZ
# ============================================================================
def actualizar_sp(val):
    """Cambia la consigna (set-point) y su punto de operación asociado."""
    global set_point, y_operacion
    set_point = val
    y_operacion = val

def actualizar_kp(val):
    """Cambia en caliente la ganancia proporcional del controlador."""
    global Kp_actual
    Kp_actual = val

def actualizar_ki(val):
    """Cambia en caliente la ganancia integral del controlador."""
    global Ki_actual
    Ki_actual = val

def actualizar_p_amp(val):
    """Cambia la amplitud del próximo pulso de perturbación."""
    global pert_amplitud
    pert_amplitud = val

def actualizar_p_dur(val):
    """Cambia la duración del próximo pulso de perturbación."""
    global pert_duracion
    pert_duracion = val

def aplicar_carga(event):
    """Dispara manualmente un pulso de perturbación (consumo de biomasa)."""
    global perturbacion_activa, tiempo_inicio_perturbacion
    if not perturbacion_activa and not simulacion_en_pausa:
        perturbacion_activa = True
        tiempo_inicio_perturbacion = tiempo_actual

def alternar_pausa(event):
    """Pausa o reanuda el avance de la simulación."""
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

def reiniciar_simulacion(event):
    """Vacía el historial y vuelve todas las variables de estado a cero,
    respetando los valores actuales de los sliders."""
    global t_data, r_data, y_data, e_data, u_data, d_data
    global integral, tiempo_actual, y_actual
    global perturbacion_activa, simulacion_en_pausa, set_point, y_operacion, pagina_actual

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

    # 3. Resetear variables de estado al valor actual del slider
    integral = 0.0
    tiempo_actual = 0.0
    set_point = slider_sp.val
    y_operacion = set_point
    y_actual = 0.0

    perturbacion_activa = False
    simulacion_en_pausa = False
    pagina_actual = 0

    # 4. Reajustar botones e interfaz
    btn_pausa.label.set_text('PAUSAR SISTEMA')
    btn_pausa.color = 'gold'
    btn_pausa.hovercolor = 'orange'

    for ax in axs:
        ax.set_xlim(0, VENTANA)

    # 5. Redibujar el lienzo completamente limpio
    fig.canvas.draw_idle()


# Conectar cada widget con su callback
slider_sp.on_changed(actualizar_sp)
slider_kp.on_changed(actualizar_kp)
slider_ki.on_changed(actualizar_ki)
slider_p_amp.on_changed(actualizar_p_amp)
slider_p_dur.on_changed(actualizar_p_dur)
btn_pert.on_clicked(aplicar_carga)
btn_pausa.on_clicked(alternar_pausa)
btn_reset.on_clicked(reiniciar_simulacion)


# ============================================================================
# BLOQUE 10: ANIMACIÓN
# ============================================================================
# blit=True mantiene la velocidad alta (solo redibuja las líneas en cada
# cuadro). El eje X solo se redibuja por completo en el instante puntual
# en que cambia de página (ver BLOQUE 7), así que el rendimiento no se ve afectado.
ani = FuncAnimation(fig, actualizar_simulacion, blit=True, interval=30, cache_frame_data=False)
plt.show()