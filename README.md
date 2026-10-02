# Proyecto LoRa & Seguimiento Satelital - GINTEA

Repositorio del proyecto de desarrollo con tecnología **LoRa** y estación de seguimiento satelital para **GINTEA**.

## Hardware Identificado

A partir de la placa utilizada en el laboratorio, las especificaciones técnicas son:

- **Modelo:** Heltec WiFi LoRa 32 (V3) — `HTIT-WB32LAF`
- **Microcontrolador:** ESP32-S3FN8 (WiFi + BLE, USB-C)
- **Transceptor LoRa:** Semtech **SX1262** (Versión `HF`: banda **863~928 MHz**, típicamente **915 MHz** en Argentina)
- **Pantalla Integrada:** OLED 0.96" 128x64 píxeles por I2C (controlador SSD1306)
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
├── hardware/                       # Modelos 3D y planos de la base rotativa de seguimiento satelital
│   └── .gitkeep
├── .gitignore
└── README.md
```

## Cómo correr el código de prueba

Podés abrir el proyecto tanto en **Arduino IDE** como en **PlatformIO**:

1. **Con Arduino IDE:**
   - Abrí `codigo_prueba/prueba_heltec_v3/prueba_heltec_v3.ino`.
   - Seleccioná la placa **Heltec WiFi LoRa 32(V3)** (del paquete ESP32 de Espressif/Heltec).
   - Instalá desde el Gestor de Librerías: **`RadioLib`** (de Jan Gromes) y **`U8g2`** (de olikraus).
2. **Con PlatformIO (VS Code):**
   - Abrí la carpeta `codigo_prueba/` en PlatformIO; las librerías y la placa se descargan automáticamente según `platformio.ini`.
