# Proyecto LoRa & Seguimiento Satelital - GINTEA

Repositorio del proyecto de desarrollo con tecnología **LoRa** y estación de seguimiento satelital para **GINTEA**.

La placa funciona como **estación terrena de [TinyGS](https://tinygs.com)**, una red abierta de estaciones LoRa que reciben telemetría de satélites. Más adelante se le va a sumar una base rotativa para apuntar una antena direccional al satélite.

## Estado actual

- [x] Placa identificada y probada con el código de prueba: OLED, SX1262, transmisión LoRa, LED y botón PRG.
- [x] Firmware TinyGS (release `2603242`) grabado, configurado y conectado a la red (MQTT).
- [x] Scripts de terminal para grabar, monitorear y mandar comandos a la placa (`scripts/`).
- [ ] Instalar la estación en la facultad (cambiar el WiFi; ver [Mudar la estación a otra red](#mudar-la-estación-a-otra-red)).
- [ ] Conseguir una placa y una antena de **433 MHz** (ver [Banda de frecuencia](#banda-de-frecuencia)).
- [ ] Diseñar la base rotativa de seguimiento (`hardware/`).

## Hardware Identificado

A partir de la placa utilizada en el laboratorio, las especificaciones técnicas son:

- **Modelo:** Heltec WiFi LoRa 32 (V3) — `HTIT-WB32LAF`
- **Microcontrolador:** ESP32-S3FN8 (WiFi + BLE, USB-C)
- **Transceptor LoRa:** Semtech **SX1262** (Versión `HF`: banda **863~928 MHz**, típicamente **915 MHz** en Argentina)
- **Pantalla Integrada:** OLED 0.96" 128x64 píxeles por I2C (controlador SSD1306)
- **Puente USB-serie:** CP2102 (USB `10C4:EA60`)
- **Gestión de Batería:** Conector JST SH1.25 de 2 pines para batería Li-Po de 3.7V

> [!CAUTION]
> **Importante:** Asegurate de tener siempre conectada la antena LoRa (conector U.FL / IPEX) antes de alimentar o transmitir con la placa para evitar dañar el amplificador de radiofrecuencia del SX1262.

### Pinout Interno de la Placa (`HTIT-WB32LAF`)

| Periférico | Señal | GPIO (ESP32-S3) | Notas |
| :--- | :--- | :---: | :--- |
| **Control de Energía** | `Vext` | `GPIO 36` | Activo en `LOW` (enciende el OLED) |
| **Pantalla OLED (I2C)** | `SDA` / `SCL` / `RST` | `17` / `18` / `21` | Dirección I2C: `0x3C` |
| **LoRa SX1262 (SPI)** | `SCK` / `MISO` / `MOSI` | `9` / `11` / `10` | Bus SPI dedicado |
| **LoRa SX1262 (Control)**| `NSS (CS)` / `RST` | `8` / `12` | Chip Select y Reset |
| **LoRa SX1262 (Estado)** | `DIO1 (IRQ)` / `BUSY` | `14` / `13` | Interrupción y estado del SX1262 |
| **Placa** | `LED Blanco` / `Botón PRG` | `35` / `0` | LED de estado y botón de usuario |

---

## Estructura del Repositorio

```text
gintea/
├── codigo_prueba/                  # Firmware inicial de prueba para la Heltec WiFi LoRa 32 V3
│   ├── platformio.ini              # Configuración lista para usar en PlatformIO (VS Code)
│   └── prueba_heltec_v3/
│       └── prueba_heltec_v3.ino    # Sketch para Arduino IDE / PlatformIO (OLED + LoRa SX1262)
├── scripts/                        # Herramientas de terminal para la estación TinyGS
│   ├── tinygs.py                   # Grabar, monitorear y mandar comandos a la placa
│   └── requirements.txt            # Dependencias de Python (pyserial, esptool)
├── hardware/                       # Modelos 3D y planos de la base rotativa de seguimiento satelital
│   └── .gitkeep
├── .gitignore
└── README.md
```

## Cómo correr el código de prueba

> El código de prueba y TinyGS ocupan la misma flash: grabar uno borra el otro.

Podés abrir el proyecto tanto en **Arduino IDE** como en **PlatformIO**:

1. **Con Arduino IDE:**
   - Abrí `codigo_prueba/prueba_heltec_v3/prueba_heltec_v3.ino`.
   - Seleccioná la placa **Heltec WiFi LoRa 32(V3)** (del paquete ESP32 de Espressif/Heltec).
   - Instalá desde el Gestor de Librerías: **`RadioLib`** (de Jan Gromes) y **`U8g2`** (de olikraus).
2. **Con PlatformIO (VS Code):**
   - Abrí la carpeta `codigo_prueba/` en PlatformIO; las librerías y la placa se descargan automáticamente según `platformio.ini`.
3. **Con `arduino-cli`** (terminal, core `esp32:esp32` instalado):
   ```bash
   arduino-cli lib install RadioLib U8g2
   arduino-cli compile --fqbn esp32:esp32:heltec_wifi_lora_32_V3 codigo_prueba/prueba_heltec_v3
   arduino-cli upload  --fqbn esp32:esp32:heltec_wifi_lora_32_V3 -p <PUERTO> codigo_prueba/prueba_heltec_v3
   ```

Al arrancar, el OLED muestra `LoRa OK (Escuchando)` y queda recibiendo a 915 MHz. Con el botón **PRG** se transmite un paquete de prueba (`GINTEA #n`).

---

## Estación TinyGS

### 1. Instalar los scripts

Hace falta Python 3.9 o más nuevo:

```bash
pip install -r scripts/requirements.txt
```

### 2. Grabar el firmware

Conectá la placa por USB-C con un cable de **datos**; los cables que solo cargan no sirven. Verificá que la detecte:

```bash
python scripts/tinygs.py puertos
```

La placa aparece marcada como `<-- Heltec V3 (CP2102)`. En Windows es un `COMx` y en Linux, `/dev/ttyUSB0`. Si no aparece, revisá el cable. En Windows puede faltar el driver CP210x de Silicon Labs.

Para grabar TinyGS:

```bash
python scripts/tinygs.py flashear
```

El script baja de GitHub la última release oficial para ESP32-S3 (`tinygs-ESP32-S3-<versión>-full.bin`), **verifica su SHA-256**, borra la flash y graba el binario en `0x0`. Antes de borrar pide confirmación, porque **se pierde la configuración guardada**. Con `--version <tag>` se elige otra release, y con `--puerto` se fuerza un puerto.

> Como alternativa sin scripts, está el instalador web oficial: <https://installer.tinygs.com> (Chrome o Edge).

### 3. Configuración inicial (portal WiFi)

Con la placa sin configurar:

1. Con el celular, conectate a la red WiFi abierta **`My TinyGS`**.
2. Entrá a **http://192.168.4.1** (si no se abre solo) y completá:

| Campo | Qué poner |
| :--- | :--- |
| GroundStation Name | Nombre público de la estación (solo letras, números y `_`, menos de 21 caracteres) |
| Password for this dashboard | Contraseña nueva del panel (mín. 8 caracteres). El usuario es siempre `admin` |
| WiFi SSID / password | Red de **2,4 GHz** con contraseña común (WPA2-PSK) |
| Latitude / Longitude | Ubicación de la estación, 3 decimales (en Argentina ambas son negativas). Es pública |
| Time Zone | `America/Argentina/...` |
| MQTT Username / Password | **Dejar vacíos**; se completan solos con el OTP (paso 4) |
| Board type | `433MHz HELTEC LORA32 V3` (es la única opción V3; los pines son los correctos) |
| OLED Bright | `50` (menos de 100 para no gastar la pantalla) |
| Enable TX | **Destildado**: transmitir requiere licencia de radioaficionado |
| Advanced Config | Vacío |

3. **Apply**. La placa se reinicia y se conecta a la red indicada.

### 4. Registrar la estación en TinyGS (OTP)

Cuando la placa tiene internet y todavía no tiene credenciales MQTT, genera un **código OTP de 6 dígitos**. Se ve en la pantalla, en el panel local y con el script:

```bash
python scripts/tinygs.py comando otp
```

1. **Cuenta:** en Telegram, unite al grupo <https://t.me/tinyGScom> y abrí un chat privado con `@tinygs_personal_bot`. Mandale `/weblogin` y te devuelve un link personal para entrar a <https://app.tinygs.com>. **Ese link no se comparte.**
2. En la consola web, andá a tu perfil → **Register New Station**. Cargá el OTP, el nombre, la ubicación, la contraseña de admin y la zona horaria. Estos datos **reemplazan** a los del portal.
3. La placa consulta cada unos 15 s, baja las credenciales y se conecta. En el monitor aparece `Connected to MQTT!`.

> El OTP cambia en cada reinicio y vence a los 30 minutos. Si se vence, reiniciá la placa (`python scripts/tinygs.py comando reiniciar`) y usá el código nuevo.
> Plan B: pedirle `/mqtt` al bot y cargar usuario y contraseña a mano en el panel.

### 5. Verificar que funciona

```bash
python scripts/tinygs.py monitor --segundos 60
```

Salida esperada:

```text
TinyGS Version 2603242 - 2603242
[SX12xx] Initializing ...
Attempting MQTT connection...
Connected to MQTT!
[SX1262] Starting to listen to <satélite> @ LoRa mode @ <frecuencia> MHz
```

El servidor elige qué satélite escuchar. La estación también aparece en el mapa de <https://tinygs.com>, y con `/stations` en el bot se ve su estado.

### Referencia de los scripts

| Comando | Qué hace |
| :--- | :--- |
| `python scripts/tinygs.py puertos` | Lista los puertos serie y marca la placa |
| `python scripts/tinygs.py descargar [--version TAG]` | Descarga y verifica el firmware (queda en `scripts/firmware/`, ignorado por git) |
| `python scripts/tinygs.py flashear [--puerto P] [--version TAG] [--si]` | Borra la flash y graba TinyGS |
| `python scripts/tinygs.py monitor [--segundos N] [--sin-reiniciar] [--mostrar-todo]` | Muestra la salida serie (Ctrl+C para salir). Oculta contraseñas salvo con `--mostrar-todo` |
| `python scripts/tinygs.py comando reiniciar` | Reinicia la placa (`!b`) |
| `python scripts/tinygs.py comando otp` | Muestra el código OTP (`!o`) |
| `python scripts/tinygs.py comando weblogin` | Pide un link de acceso al panel (`!w`). No compartirlo |
| `python scripts/tinygs.py comando borrar-config` | Borra toda la configuración y reinicia (`!e`) |
| `python scripts/tinygs.py comando paquete-prueba` | Transmite un paquete de prueba (`!p`, solo con TX habilitado) |

> **Ojo:** en esta placa, abrir el puerto serie **reinicia el ESP32** (la línea RTS del CP2102 maneja el reset). Por eso `monitor` y `comando` muestran siempre el arranque completo.

### Mudar la estación a otra red

La configuración guarda **una sola red WiFi**. Para cambiarla:

- **Desde la red actual:** entrá al panel con la IP de la placa (usuario `admin` y la contraseña del panel) y cambiá el SSID y la clave.
- **Si no se puede conectar** (por ejemplo, porque ya está en el lugar nuevo): mantené apretado **PRG 8 segundos**. Levanta el AP de rescate `My TinyGS` sin contraseña en `192.168.4.1`. Cambiá el WiFi y reiniciala.

Redes que **no sirven**: eduroam o cualquier red WPA2-Enterprise (con usuario y contraseña), redes con portal de login en el navegador y redes solo de 5 GHz. Si la red de la facultad es así, hace falta un router o una red aparte para la estación.

Las credenciales MQTT y el registro quedan guardados al cambiar de red. Solo se pierden con `borrar-config` o al volver a flashear.

### Banda de frecuencia

Esta placa es la versión **HF (863–928 MHz)**. Según TinyGS, más del 90 % de los satélites LoRa activos transmiten en **400–437 MHz**, y la propia documentación advierte que con una placa de otra banda probablemente no se reciba nada por la adaptación de RF. Al registrarse, el servidor la puso a escuchar en 438 MHz. La estación funciona y queda online, pero para recibir paquetes conviene una **Heltec V3 de 433 MHz** y una antena para esa banda; la antena de fábrica tampoco es la recomendada.

### Seguridad

- No subir al repo ni mandar por chat la contraseña del panel, las credenciales MQTT ni los links de `/weblogin`: dan acceso a la estación o a la cuenta.
- **Enable TX** queda desactivado salvo que haya un operador con licencia.
