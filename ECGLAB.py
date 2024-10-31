import sys
from PyQt6 import uic, QtCore, QtWidgets
from PyQt6.QtWidgets import QMainWindow, QApplication, QVBoxLayout, QWidget, QFileDialog
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import pywt
import matplotlib.pyplot as plt
import serial.tools.list_ports
import serial
import numpy as np
import struct
import threading
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy.signal import firwin, lfilter, find_peaks
import datetime

class principal(QMainWindow):

    def __init__(self):
        super(principal, self).__init__()
        uic.loadUi("ECGW.ui", self)
        self.puertos_disponibles()
        self.ser1 = None
        self.connect.clicked.connect(self.conectar)

        self.guardarButton.clicked.connect(self.guardar_datos)
        self.cargarButton.clicked.connect(self.cargar_y_mostrar_datos)
        self.espectrogramaButton.clicked.connect(self.calcular_espectrograma)


        self.fm = 100  # Frecuencia de muestreo (100 Hz)
        self.duracion = 300 #(segundos)

        # Crear eje X en tiempo (segundos)
        self.x = np.linspace(0, self.duracion, int(self.duracion * self.fm))
        self.y = np.zeros(int(self.duracion * self.fm))

        # Configurar el gráfico
        self.fig = Figure()
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.graficawidget.setLayout(layout)

        # Configuración del filtro FIR pasabanda con ventana Hanning
        self.fc_baja = 0.5  
        self.fc_alta = 45   

        # Normalizar las frecuencias de corte
        self.fn_baja = self.fc_baja / (0.5 * self.fm)
        self.fn_alta = self.fc_alta / (0.5 * self.fm)

        self.orden_fir = 1

        # Crear el filtro FIR con ventana Hanning
        self.b_fir = firwin(self.orden_fir, [self.fn_baja, self.fn_alta], pass_zero=False, window="hann")

        # Establecer umbral para la detección de peaks
        self.umbral = 2065

    def puertos_disponibles(self):
        p = serial.tools.list_ports.comports()
        for port in p:
            self.puertos.addItem(port.device)

    def conectar(self): 
        estado = self.connect.text()
        self.stop_event_ser1 = threading.Event()
        if estado == "CONECTAR":
            com = self.puertos.currentText()
            try:
                self.ser1 = serial.Serial(com, 115200)
                self.hilo_ser1 = threading.Thread(target=self.periodic_thread1)
                self.hilo_ser1.start()
                print("Puerto serial 1 Conectado")
                self.connect.setText("DESCONECTAR")

            except serial.SerialException as e:
                print("Error en el puerto serial 1: ", e)
        else:
            self.ser1.close()
            self.stop_event_ser1.set()
            self.hilo_ser1.join()
            print("Puerto serial 1 Desconectado")
            self.connect.setText("CONECTAR")

    def periodic_thread1(self):
        if self.ser1 is not None and self.ser1.is_open:
            data = self.ser1.read(50)
            if len(data) == 50:
                data = struct.unpack('50B', data)
                for i in range(0, len(data), 2):
                    self.y = np.roll(self.y, -1)
                    self.y[-1] = data[i] * 100 + data[i + 1]

                self.ax.clear()

                # Aplicar el filtro FIR con ventana Hanning a los datos en tiempo real
                df = lfilter(self.b_fir, 1.0, self.y)

                # Graficar la señal filtrada en función del tiempo
                self.ax.plot(self.x, df)
                self.ax.set_xlabel('Tiempo (s)')
                self.ax.set_ylabel('Amplitud')
                self.ax.set_title('Señal en Tiempo Real')
                self.ax.grid(True)
                self.canvas.draw()

        if not self.stop_event_ser1.is_set():
            threading.Timer(1e-3, self.periodic_thread1).start()

    def guardar_datos(self):
        try:
            now = datetime.datetime.now()
            fecha_hora = now.strftime("%Y-%m-%d %H:%M:%S")
            nombre_persona = self.nombre_persona.text()
            nombre_persona = nombre_persona.replace(":", "").replace(" ", "_")
            nombre_archivo = f"{nombre_persona}.txt"

            with open(nombre_archivo, 'w') as f:
                f.write(f"Fecha y hora: {fecha_hora}\n")
                f.write(f"Nombre del paciente: {nombre_persona}\n")
                f.write("Datos de la medición:\n")
                for i in range(len(self.x)):
                    f.write(f"{self.x[i]}, {self.y[i]}\n")

            print(f"Datos guardados en {nombre_archivo}")

        except Exception as e:
            print("Error al guardar los datos:", e)

    def cargar_datos(self, nombre_archivo):
        try:
            tiempo, amplitud = np.loadtxt(nombre_archivo, delimiter=',', unpack=True, skiprows=3)

            # Detectar peaks en la señal atenuada
            peaks, _ = find_peaks(amplitud, height=self.umbral)
            numero_peaks = len(peaks)
            print(f"Número de peaks detectados: {numero_peaks}")

            dpeaks = np.diff(peaks) / self.fm  
            self.HVR(dpeaks)

            return tiempo, amplitud

        except Exception as e:
            print("Error al cargar los datos:", e)
            return None, None

    def cargar_y_mostrar_datos(self):
        nombre_archivo, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo", "", "Archivos de texto (*.txt)")
        if nombre_archivo:
            x, y = self.cargar_datos(nombre_archivo)
            if x is not None and y is not None:
                self.x = np.linspace(0, len(y) / self.fm, len(y))  
                self.y = y
                
                peaks, _ = find_peaks(self.y, height=self.umbral)
                
                self.ax.clear()
                self.ax.plot(self.x, self.y, label="Señal cargada")
                self.ax.plot(self.x[peaks], self.y[peaks], 'ro', label="Picos detectados")
                self.ax.set_xlabel('Tiempo (s)')
                self.ax.set_ylabel('Valor')
                self.ax.set_title('Datos cargados desde archivo')
                self.ax.legend()
                self.canvas.draw()

                self.y_filtrada = lfilter(self.b_fir, 1.0, self.y)

            else:
                print(f"No se pudieron cargar los datos desde {nombre_archivo}")

    def calcular_espectrograma(self):
        try:
            if not isinstance(self.y, np.ndarray):
                self.y = np.array(self.y)
            
            if self.y.size == 0:
                print("No hay datos suficientes para calcular el espectrograma.")
                return
            
            # Copiar y atenuar valores de amplitud para el espectrograma
            y_atenuada = np.array([0 if 0 <= x <= 2000 else x for x in self.y])
            
            scales = np.arange(1, 40)
            wavelet = 'cmor1.5-1.0'  
            coeficientes, freqs = pywt.cwt(y_atenuada, scales, wavelet, sampling_period=1/self.fm)

            plt.figure(figsize=(12, 6))
            plt.imshow(np.abs(coeficientes), extent=[self.x[0], self.x[-1], scales.min(), scales.max()],
                       cmap='jet', aspect='auto', interpolation='bilinear')
            plt.colorbar(label='Magnitud')
            plt.xlabel("Tiempo (s)")
            plt.ylabel("Escala")
            plt.title("Transformada Wavelet Continua usando Morlet")
            plt.show()

        except Exception as e:
            print("Error al calcular el espectrograma:", e)

    def HVR(self, dpeaks):
        print ("Parámetros de HVR:")
        if len(dpeaks) == 0:
            print("No hay suficientes datos de picos R-R para calcular los parámetros HRV.")
            return

        m_rr = np.mean(dpeaks)
        sdnn = np.std(dpeaks)
        rmssd = np.sqrt(np.mean(np.diff(dpeaks) ** 2))
        nn50 = np.sum(np.abs(np.diff(dpeaks)) > 0.05)
        pnn50 = (nn50 / len(dpeaks)) * 100

        print(f"Media entre peaks: {m_rr:.2f} s")
        print(f"Desviación Estándar de los Intervalos R-R (SDNN): {sdnn:.2f} s")
        print(f"Raíz Cuadrada de la Media de las Diferencias Sucesivas (RMSSD) : {rmssd:.2f} s")
        print(f"pNN50: {pnn50:.2f}%")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    GUI = principal()
    GUI.show()
    sys.exit(app.exec())


