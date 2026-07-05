# Simulación del Control de Oxígeno Disuelto en Acuicultura (RAS)

Este programa simula, en una ventana interactiva, el lazo de control de oxígeno
disuelto descripto en el trabajo **"Sistema de Control de Oxígeno en
Acuicultura"** (UTN-BA, Tecnologías para la Automatización, 2026). Corresponde
al diagrama de bloques de la **Figura 1** del informe: un controlador PID
compara el oxígeno medido contra el set-point (7 mg/L) y ajusta la frecuencia
del aireador para corregir el error, incluso cuando aparecen perturbaciones
(por ejemplo, un pico de consumo por alimentación de los peces).

El programa muestra, en cuatro gráficos apilados, las **4 señales del lazo**:

1. **y(t) — Respuesta**: el oxígeno disuelto medido, junto con el set-point
   r(t) y una banda de tolerancia (umbral inferior / superior). Mientras y(t)
   se mantiene dentro de la banda, el sistema está en estado **NORMAL**
   (hay error, pero es tolerable). Si y(t) sale de esa banda —por ejemplo por
   una perturbación muy fuerte o un PID mal sintonizado— el sistema pasa a
   estado de **FALLA** (hipoxia severa o sobresaturación crítica), y esto se
   avisa en pantalla en rojo.
2. **e(t) — Señal de error**: r(t) − y(t).
3. **d(t) — Perturbación**: el evento de caída de oxígeno que se dispara con
   el botón "Aplicar perturbación".
4. **u(t) — Señal de entrada**: la frecuencia que el PID le manda al variador
   del aireador (después del tiempo muerto del proceso).

No hace falta saber programar para usarlo: se abre una ventana con gráficos y
controles (sliders y botones) que se mueven con el mouse.

---

## 1. Qué vas a necesitar

- Tener **Python 3** instalado en la computadora (versión 3.8 o superior).
- Las librerías `matplotlib` y `numpy`.

### ¿Cómo sé si tengo Python instalado?

Abrí una terminal (en Windows: *Símbolo del sistema* o *PowerShell*; en Mac:
*Terminal*; en Linux: *Terminal*) y escribí:

```
python3 --version
```

Si te muestra algo como `Python 3.11.4`, ya lo tenés. Si da error, hay que
instalarlo desde [python.org/downloads](https://www.python.org/downloads/)
(al instalar en Windows, marcar la casilla **"Add Python to PATH"**).

---

## 2. Instalar las librerías necesarias

Con la terminal abierta, escribí:

```
pip install matplotlib numpy
```

(En algunos sistemas puede ser `pip3` en vez de `pip`.)

Esto solo hay que hacerlo **una vez** por computadora.

---

## 3. Cómo ejecutar la simulación

1. Guardá el archivo `simulacion_oxigeno_ras.py` en una carpeta que encuentres
   fácil (por ejemplo, el Escritorio).
2. Abrí la terminal **ubicado en esa misma carpeta**. Por ejemplo, si el
   archivo está en el Escritorio:
   ```
   cd Desktop
   ```
3. Ejecutá:
   ```
   python3 simulacion_oxigeno_ras.py
   ```
4. Se va a abrir una ventana con dos gráficos (arriba el oxígeno disuelto,
   abajo la frecuencia del aireador) y varios controles a la derecha.

---

## 4. Cómo usar la ventana

### Botones (abajo a la derecha)

| Botón | Qué hace |
|---|---|
| **Play / Pausa** | Arranca o detiene el avance del tiempo simulado. Al arrancar, vas a ver cómo el oxígeno y la frecuencia del aireador evolucionan en tiempo real en el gráfico. |
| **Reset** | Vuelve todo al estado inicial (tiempo = 0, oxígeno estabilizado, sin perturbaciones). |
| **Aplicar perturbación** | Dispara, en el instante en que lo apretás, una caída de oxígeno con la amplitud y duración que hayas configurado en los sliders (simula, por ejemplo, un evento de alimentación). |

### Sliders (controles deslizables)

| Slider | Qué representa |
|---|---|
| **Kp** | Ganancia proporcional del controlador: cuánto reacciona el controlador ante el error actual. |
| **Ki** | Ganancia integral: cuánto corrige el controlador el error acumulado en el tiempo (es la que garantiza que el error final sea cero). |
| **Kd** | Ganancia derivativa: cuánto anticipa el controlador según la velocidad de cambio del error (el informe usa un PI puro, o sea Kd = 0, pero podés experimentar). |
| **Set-point r** | El valor de oxígeno disuelto que el sistema debe mantener (por defecto 7 mg/L). |
| **Amplitud pert. [mg/L]** | Cuántos mg/L de oxígeno "cae" el estanque durante el evento de perturbación (usá valores negativos, ej. −1.5, para simular una caída). |
| **Duración pert. [s]** | Durante cuántos segundos se aplica esa caída antes de dejar de sumar perturbación. |
| **Umbral inf.** | Límite inferior de la banda de oxígeno considerada "normal" (por defecto 5.0 mg/L, valor de hipoxia severa según el informe). Por debajo de este valor, el sistema pasa a estado de **FALLA**. |
| **Umbral sup.** | Límite superior de la banda "normal" (por defecto 9.0 mg/L). Por encima de este valor, el sistema también pasa a estado de **FALLA** (sobresaturación). |

**Importante:** los sliders se pueden mover en cualquier momento, incluso con
la simulación corriendo — vas a ver el efecto inmediatamente en el gráfico.

### Lectura en vivo

Arriba de la ventana se muestra en todo momento, en una sola línea:

```
t=... s  y=... mg/L  e=... mg/L  u=... Hz  d=... mg/L·s⁻¹   |   Estado: NORMAL / FALLA
```

### ¿Qué diferencia hay entre "error" y "falla"?

- Mientras el controlador está corrigiendo una perturbación, **siempre** hay
  algo de error (e(t) ≠ 0) — eso es normal y esperable, es justamente lo que
  el PID va corrigiendo con el tiempo.
- El programa define una **banda de tolerancia** entre el "Umbral inf." y el
  "Umbral sup." (franja verde clara en el gráfico de arriba). Mientras y(t)
  se mantenga dentro de esa banda, el estado es **NORMAL**, aunque haya
  error.
- Si y(t) se escapa de esa banda (por ejemplo, una perturbación demasiado
  grande, una duración muy larga, o ganancias del PID mal elegidas que no
  alcanzan a corregir a tiempo), el estado pasa a **FALLA**: la línea de
  y(t) se pone roja y el texto de arriba avisa "⚠ FALLA (fuera de umbral)".
  Esto representa, físicamente, un evento de hipoxia severa (si y(t) cae
  por debajo del umbral inferior) o de sobresaturación crítica (si sube por
  encima del umbral superior).

---

## 5. Ejemplo de uso típico (para reproducir el escenario del informe)

1. Ejecutar el script.
2. Dejar Kp = 2.5, Ki ≈ 0.0139 (equivale a Ti = 180 s) y Kd = 0, que son los
   valores usados en el informe.
3. Apretar **Play** y esperar a que el oxígeno se estabilice en 7 mg/L.
4. Configurar **Amplitud pert.** en −1.5 y **Duración pert.** en 300 (segundos),
   simulando el evento de alimentación descripto en la sección 6.3.2 del
   informe.
5. Apretar **Aplicar perturbación** y observar cómo el oxígeno cae y el
   controlador PID lo recupera en pocos minutos, mientras la frecuencia del
   aireador (gráfico de abajo) sube para compensar.
6. Probar bajar Ki a 0 y repetir el paso 5: se puede ver cómo, sin acción
   integral, el sistema queda con un error permanente (no vuelve exactamente
   a 7 mg/L), demostrando por qué el informe elige un controlador PI y no uno
   puramente proporcional.
7. Para ver una **FALLA** en acción: subir la amplitud de la perturbación a
   −3.0 mg/L, la duración a 500 s, y bajar Kp a 0.5. Al aplicar la
   perturbación, el oxígeno cae por debajo del umbral inferior (5.0 mg/L) y
   la línea se pone roja: eso simula un evento de hipoxia severa que el
   controlador, mal sintonizado, no llega a corregir a tiempo.

---

## 6. Problemas comunes

- **"python3: command not found"** → Probar con `python` en vez de
  `python3`, o reinstalar Python marcando la opción de agregarlo al PATH.
- **"No module named matplotlib"** → Falta correr `pip install matplotlib
  numpy` (paso 2).
- **La ventana no responde / va lenta** → Es normal si hay muchas otras
  aplicaciones abiertas; cerrar y volver a ejecutar el script suele
  solucionarlo.
- **Quiero cerrar el programa** → Simplemente cerrar la ventana del gráfico.

---

## 7. Qué modelo matemático usa por detrás (para quien quiera más detalle)

El proceso (estanque + aireador) se modela como un sistema de primer orden
con tiempo muerto, linealizado alrededor del punto de operación normal
(7 mg/L, 30 Hz), según la sección 6.2 del informe:

```
τ · d(Δy)/dt = −Δy + K · Δu(t − θ)
```

con τ = 300 s, θ = 30 s y K = 0.08 (mg/L)/Hz. El controlador aplica la ley
PID clásica con anti-windup (para que el término integral no se "vuelva
loco" cuando el aireador está al máximo o al mínimo), igual que el bloque
PID_Compact configurado en el PLC Siemens S7-1200 descripto en la sección
5.1.2 del informe.