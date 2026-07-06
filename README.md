
# UTN.BA - SIMULACIÓN INTERACTIVA DE CONTROL DE OXÍGENO EN RAS

Este proyecto contiene el script de simulación dinámica en tiempo real para el control de Oxígeno Disuelto (OD) mediante un controlador PI con Anti-Windup, parametrizado bajo las especificaciones técnicas del informe de la cátedra.

La interfaz gráfica interactiva permite modificar parámetros de sintonía (Kp, Ki), el Set-point, y disparar perturbaciones dinámicas (simulando consumo de biomasa) para evaluar la estabilidad del sistema.


## 🚀 GUÍA DE INSTALACIÓN Y EJECUCIÓN (PASO A PASO)

Siga estas instrucciones para clonar el repositorio, configurar el entorno virtual y ejecutar la simulación en su computadora.

### PASO 1: CLONAR EL REPOSITORIO

Abra la terminal (Consola de comandos, PowerShell o Git Bash) y ejecute el siguiente comando para clonar el proyecto:
```
git clone https://github.com/delfisartorio/TP-Final-TPA.git
```
Luego, ingrese a la carpeta del proyecto ejecutando:
```
cd TP-Final-TPA
```
(Si lo clonaste en Downloads por ejemplo el comando quedaria: cd "C:\Users\tuUser\Downloads\TP-Final-TPA")

### PASO 2: CREAR UN ENTORNO VIRTUAL (RECOMENDADO)

Para evitar conflictos con otras librerías de su sistema, cree un entorno virtual de Python ejecutable desde la carpeta del proyecto:

* En Windows:
```
  python -m venv venv
  venv\Scripts\activate
  ```

* En macOS / Linux:
```
  python3 -m venv venv
  source venv/bin/activate
  ```

Una vez activado, verá el texto "(venv)" al principio de la línea de comandos de su terminal.


### PASO 3: INSTALAR LAS DEPENDENCIAS

El script requiere librerías específicas de procesamiento numérico y visualización matemática. Instálelas ejecutando el siguiente comando:

```
pip install numpy matplotlib
```

### PASO 4: EJECUTAR LA SIMULACIÓN

Con el entorno activo y las librerías instaladas, lance el script principal:

```
python simulacion_oxigeno_ras.py
```

## 🎛️ GUÍA DE USO DEL PANEL DE CONTROL


Una vez abierta la ventana de la simulación, dispondrá de las siguientes herramientas interactivas:

* SLIDERS DE CONTROL:
  - Set-point (r): Modifica el objetivo de Oxígeno Disuelto dentro del rango estricto de 6.0 a 8.0 mg/L.
  - Ganancias (Kp y Ki): Permiten cambiar en caliente la sintonía del lazo cerrado para observar sobreimpulsos, oscilaciones o el amortiguamiento del sistema de forma inmediata.
  - Configuración de Perturbación: Deslizadores para preconfigurar la amplitud y el tiempo de duración del pulso de carga biológica.

* BOTONES DE ACCIÓN:
  - DISPARAR PERTURBACIÓN: Aplica un pulso de consumo de oxígeno basado en los valores configurados en los sliders.
  - PAUSAR / REANUDAR SISTEMA: Congela la simulación en tiempo real para analizar detalladamente las curvas de error o la salida del variador Siemens.
  - REINICIAR: Limpia el historial de datos dinámicos, elimina las curvas anteriores (evitando líneas fantasma) y resetea el tiempo a cero utilizando las condiciones iniciales actuales configuradas en los sliders.

