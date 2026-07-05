# Simulador de lazo PI — Oxígeno Disuelto en RAS

Archivo: `simulador_OD_RAS.html`

## Cómo abrirlo

**No hace falta ningún archivo `.js` aparte, ni internet, ni instalar nada.**
Todo el código (HTML + CSS + JavaScript) está adentro de ese único archivo `.html`.

1. Descargá `simulador_OD_RAS.html`.
2. Abrilo con doble clic (se abre en tu navegador por defecto), o arrastralo a una
   pestaña nueva de Chrome / Edge / Firefox.
3. Listo, ya está corriendo. Podés moverlo, subirlo a Drive, mandarlo por mail o
   subirlo al campus — sigue funcionando igual, es un archivo autónomo.

> Si tu navegador te pregunta algo raro o lo bloquea, probá abrirlo con Chrome.
> No usa cámara, micrófono, ni guarda nada en tu computadora.

## Qué es cada parte de la pantalla

### Columna izquierda — Tablero de control

- **Referencia y controlador**
  - *Set-point r(t)*: el valor deseado de oxígeno disuelto (mg/L).
  - *Tipo de controlador*: On-Off / P / PI / PID. Cambiarlo en vivo te deja
    comparar los cuatro comportamientos con la misma perturbación.
  - *Kp*, *Ti*, *Td*: ganancias del controlador (Td solo aparece si elegís PID).
  - *Banda de tolerancia*: el ± mg/L que se dibuja como franja alrededor del
    set-point en los gráficos (el "umbral máx/mín" que pedía la consigna).

- **Perturbación (carga Rbio)**
  - *Amplitud* y *Duración*: configurás cuánto O₂ consume la perturbación en
    total y en cuánto tiempo lo hace.
  - Botón **"Aplicar perturbación ahora"**: la dispara en el instante en que
    lo tocás (podés hacerlo mientras corre o justo después de un Reset).

- **Retroalimentación**
  - *Negativa* (la correcta) vs *Positiva* (demostrativa, para ver por qué el
    lazo diverge si el signo está mal puesto).

- **Simulación**
  - **▶ Correr / ⏸ Pausar**: arranca o congela la física del lazo.
  - **⏭ Paso**: avanza 1 segundo simulado por vez (útil pausado, para analizar
    el instante exacto de una perturbación).
  - **↺ Reset**: vuelve todo al estado inicial (usa el set-point actual del
    slider como punto de partida).
  - *Velocidad*: cuántos segundos simulados corren por segundo real.
  - *Ventana visible*: cuánto tiempo hacia atrás se ve en los gráficos.

### Columna derecha — Simulación

- **Diagrama de bloques**: el mismo lazo del informe (r → Σ → controlador →
  Σ perturbación → planta → y, con la realimentación abajo). El signo del Σ
  y el color de la realimentación cambian según el toggle Negativa/Positiva.
- **Tira de lecturas**: t, r(t), y(t), e(t), u(t) y el estado del lazo
  (estable / fuera de banda / saturado / carga activa / divergiendo), todo
  actualizado en vivo.
- **Gráfico 1 — Concentración (mg/L)**: r(t), y(t), la banda de tolerancia
  sombreada y una franja violeta marcando cuándo estuvo activa la perturbación.
- **Gráfico 2 — Error e(t)**: en su propia escala (mucho más chica que la de
  concentración), con la misma banda de tolerancia alrededor del cero.
- **Gráfico 3 — Salida del controlador u(t) y carga d(t)**: u(t) en Hz con
  líneas punteadas en los límites de saturación (10 y 50 Hz), y d(t) superpuesta
  en su propia escala fina abajo.
- **Fundamentación del diseño** (desplegable, abajo de todo): el texto que
  justifica por qué PI y no On-Off/P/PID, qué es la "carga" del sistema, la
  demostración de realimentación negativa vs. positiva, el cuidado con las
  escalas, y el modelo matemático usado.

## Flujo sugerido para el TP

1. Dejá los valores por defecto (PI, Kp=2.5, Ti=180s, r=7 mg/L) y tocá
   **Correr**. Vas a ver que y(t) ya arranca en el set-point (sistema en reposo).
2. Con la simulación corriendo, configurá una perturbación (por ejemplo
   amplitud 1.5 mg/L, duración 120 s — el evento de alimentación del informe)
   y tocá **Aplicar perturbación ahora**.
3. Mirá cómo cae y(t), sube e(t) y u(t) reacciona, hasta volver al set-point.
   Pausá en el momento que quieras para leer los valores exactos en la tira
   de lecturas.
4. Cambiá el *Tipo de controlador* a **P** y repetí la perturbación: vas a ver
   que queda un error residual (no vuelve exacto a 7 mg/L). Cambialo a
   **On-Off** y vas a ver la oscilación permanente. Volvé a **PI** para
   confirmar que es el que cumple los objetivos del informe.
5. Probá tocar **Retroalimentación → Positiva** con el lazo corriendo: vas a
   ver que y(t) se dispara en vez de estabilizarse. Volvé a **Negativa** y
   dale **Reset** para seguir trabajando.
6. Usá la sección **Fundamentación del diseño** como base de texto para la
   parte del informe que pide justificar el tipo de controlador y explicar
   qué es la carga del sistema.

## Notas técnicas rápidas

- El modelo de planta es el de 1er orden con retardo del informe:
  G(s) = Kp/(τs+1)·e^(−θs), con Kp=0.08 (mg/L)/Hz, τ=300 s, θ=30 s.
- El PI tiene anti-windup por integración condicional, igual que el
  PID_Compact real (se congela la integral cuando u satura en 10 o 50 Hz).
- Paso de integración fijo: dt = 1 s (Euler explícito).
- Todo el código JS está comentado por bloques funcionales (BLOQUE 0 a 8)
  dentro del mismo `.html`, siguiendo el orden del diagrama de bloques del
  informe, por si querés mostrarlo o modificarlo.