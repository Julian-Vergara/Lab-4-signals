# Procesamiento de una señal de ECG
## Disclaimer
Los datos de las muestras utilizados en este proyecto son de mi propiedad y han sido generados a partir de mis propias mediciones. Se permite el uso y la distribución de estos datos con fines de investigación, educación y desarrollo de proyectos relacionados con el procesamiento de señales electromiográficas. Sin embargo, se solicita que se reconozca la fuente de los datos y se respete la integridad de la información. Cualquier uso comercial de estos datos requerirá mi consentimiento previo.
## Introducción
El laboratorio consistió en la elaboración de un código para el análisis de señales electrocardiograficas (ECG). Este código cuenta con varias secciones que aplican técnicas avanzadas como el uso de ventanas de filtros discretos con ventanas de Hanning,análisis espectral mediante la transformada wavelet con la función Morlet  y el funcionamiento de interfaces que operan en tiempo real. Estas herramientas permiten procesar y analizar las señales capturadas durante 5.Este proyecto tiene el potencial de ser útil en diversas aplicaciones biomédicas, como la rehabilitación.
### Adquisición de datos
Se utilizó un microcontrolador STM32 para adquirir los datos mediante un módulo ECG AD8232. El código implementado captura los datos y los empaqueta en bloques de 50 bytes (50B). Este programa opera utilizando un sistema operativo en tiempo real (RTOS) para la gestión eficiente de tareas en la STM32, lo que ayuda a evitar la congestión en la transmisión de datos. La configuración del sistema está diseñada para trabajar con una frecuencia de muestreo de 100Hz, garantizando un procesamiento continuo y en tiempo real de las señales electromiográficas.
![Interfaz pyton](In.jpeg)
La primera sección del código está diseñada para gestionar los parámetros de la interfaz gráfica, la cual permite visualizar y analizar datos en tiempo real. A través de la conexión con el puerto serial, se reciben datos provenientes del microcontrolador STM32. La interfaz muestra las señales filtradas que el microcontrolador envía, garantizando una representación clara de la información. Además, incluye botones para guardar y cargar las señales capturadas, así como para aplicar el wavelet a los pulsos detectados, lo que optimiza tanto la visualización como el análisis de las señales. Esta funcionalidad es fundamental para la interpretación precisa de los datos y el estudio de las características de las señales capturadas.
```pyton
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
        self.duracion = 300 # (segundos)

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
```
En esta sección del código, se implementa un filtro FIR (Finite Impulse Response) pasabanda diseñado específicamente para procesar señales de ECG (electrocardiograma) en tiempo real. El filtro se configura con frecuencias de corte de 0.5 Hz y 45 Hz, que son normalizadas en función de la frecuencia de muestreo de 100 Hz. Utilizando la función firwin de la biblioteca scipy.signal, se genera un filtro de orden 1 que permite el paso de frecuencias relevantes para la detección de características del ECG, mientras que atenúa las frecuencias no deseadas, como el ruido y las interferencias. Durante la adquisición de datos en tiempo real, el filtro se aplica a la señal capturada mediante la función lfilter, mejorando así la calidad de la señal del ECG y facilitando su análisis posterior.


