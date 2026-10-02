/**
 * GINTEA - Código de Prueba para Heltec WiFi LoRa 32 V3 (HTIT-WB32LAF)
 * 
 * Hardware identificado:
 *   - Placa: Heltec WiFi LoRa 32 V3 (HTIT-WB32LAF)
 *   - MCU: ESP32-S3FN8
 *   - Transceptor LoRa: Semtech SX1262 (Banda 863~928 MHz -> 915.0 MHz ISM)
 *   - Pantalla: OLED 0.96" 128x64 I2C (SSD1306)
 * 
 * Librerías requeridas (instalar desde el Library Manager de Arduino IDE o PlatformIO):
 *   1. "RadioLib" por Jan Gromes (para el chip SX1262)
 *   2. "U8g2" por olikraus (para el display OLED SSD1306)
 * 
 * IMPORTANTE: Nunca alimentar la placa sin tener la antena LoRa conectada al conector U.FL/IPEX.
 */

#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <U8g2lib.h>
#include <RadioLib.h>

// ================= PINOUT HELTEC WIFI LORA 32 V3 =================
// Pantalla OLED I2C (SSD1306 128x64)
#define OLED_SDA    17
#define OLED_SCL    18
#define OLED_RST    21

// Alimentación externa y de pantalla (Vext: activo en BAJO)
#define VEXT_PIN    36

// LED blanco integrado y botón PRG (USER)
#define LED_PIN     35
#define BTN_PRG     0

// Transceptor LoRa SX1262 (SPI interno)
#define LORA_SCK    9
#define LORA_MISO   11
#define LORA_MOSI   10
#define LORA_CS     8
#define LORA_RST    12
#define LORA_DIO1   14
#define LORA_BUSY   13

// Parámetros de radio LoRa (ajustar según frecuencia de trabajo / satélite)
#define LORA_FREQ   915.0   // Frecuencia en MHz (banda 863~928 MHz de la placa)
#define LORA_BW     125.0   // Ancho de banda en kHz
#define LORA_SF     9       // Spreading Factor (7 a 12)
#define LORA_CR     7       // Coding Rate (4/7)
#define LORA_SYNC   0x12    // Sync word privado
#define LORA_PWR    14      // Potencia TX en dBm (máx 22 dBm en SX1262)

// Instancia del display OLED
U8G2_SSD1306_128X64_NONAME_F_HW_I2C display(U8G2_R0, /* reset=*/ OLED_RST, /* clock=*/ OLED_SCL, /* data=*/ OLED_SDA);

// Instancia del módulo SX1262 usando bus SPI
SX1262 radio = new Module(LORA_CS, LORA_DIO1, LORA_RST, LORA_BUSY);

uint32_t packetCounter = 0;
bool loraReady = false;

// Encender alimentación Vext (alimenta el OLED en la Heltec V3)
void vextON() {
  pinMode(VEXT_PIN, OUTPUT);
  digitalWrite(VEXT_PIN, LOW); // LOW = ON en Heltec V3
  delay(50);
}

void actualizarPantalla(const char* estado, const String& detalle, float rssi = 0, float snr = 0) {
  display.clearBuffer();
  display.setFont(u8g2_font_6x10_tf);
  display.drawStr(0, 10, "GINTEA - LoRa SatTest");
  display.drawLine(0, 13, 128, 13);

  char freqBuf[32];
  snprintf(freqBuf, sizeof(freqBuf), "SX1262 | %.1f MHz", LORA_FREQ);
  display.drawStr(0, 26, freqBuf);

  display.drawStr(0, 40, estado);
  display.drawStr(0, 52, detalle.c_str());

  if (rssi != 0 || snr != 0) {
    char sigBuf[32];
    snprintf(sigBuf, sizeof(sigBuf), "RSSI:%.0fdBm SNR:%.1fdB", rssi, snr);
    display.drawStr(0, 63, sigBuf);
  } else {
    display.drawStr(0, 63, "PRG: Enviar paquete TX");
  }

  display.sendBuffer();
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n=== GINTEA - Prueba Heltec WiFi LoRa 32 V3 (HTIT-WB32LAF) ===");

  pinMode(LED_PIN, OUTPUT);
  pinMode(BTN_PRG, INPUT_PULLUP);
  digitalWrite(LED_PIN, HIGH);

  // 1. Encender Vext e inicializar OLED
  vextON();
  display.begin();
  actualizarPantalla("Iniciando...", "Configurando SX1262");

  // 2. Inicializar bus SPI para el SX1262
  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_CS);

  // 3. Inicializar radio LoRa SX1262
  Serial.print("[SX1262] Inicializando en ");
  Serial.print(LORA_FREQ);
  Serial.println(" MHz... ");

  int state = radio.begin(LORA_FREQ, LORA_BW, LORA_SF, LORA_CR, LORA_SYNC, LORA_PWR);
  if (state == RADIOLIB_ERR_NONE) {
    Serial.println("[SX1262] Inicializado correctamente!");
    loraReady = true;
    actualizarPantalla("LoRa OK (Escuchando)", "Esperando paquetes...");
    radio.startReceive();
  } else {
    Serial.print("[SX1262] Error al iniciar, codigo: ");
    Serial.println(state);
    actualizarPantalla("ERROR LoRa SX1262", "Cod: " + String(state));
  }

  digitalWrite(LED_PIN, LOW);
}

void loop() {
  if (!loraReady) {
    delay(1000);
    return;
  }

  // Si se presiona el botón PRG (GPIO 0), transmite un paquete de prueba
  if (digitalRead(BTN_PRG) == LOW) {
    digitalWrite(LED_PIN, HIGH);
    packetCounter++;
    String txMsg = "GINTEA #" + String(packetCounter);

    Serial.print("[TX] Enviando: ");
    Serial.println(txMsg);
    actualizarPantalla("Transmitiendo TX...", txMsg);

    int state = radio.transmit(txMsg);
    if (state == RADIOLIB_ERR_NONE) {
      Serial.println("[TX] Paquete enviado con exito!");
      actualizarPantalla("TX Completado!", txMsg);
    } else {
      Serial.print("[TX] Error al transmitir: ");
      Serial.println(state);
      actualizarPantalla("Error en TX", "Cod: " + String(state));
    }

    digitalWrite(LED_PIN, LOW);
    delay(500);
    // Volver a modo escucha continua
    radio.startReceive();
  }

  // Verificar si llegó algún paquete por recepción
  if (radio.getPacketLength() > 0) {
    String rxMsg;
    int state = radio.readData(rxMsg);

    if (state == RADIOLIB_ERR_NONE && rxMsg.length() > 0) {
      digitalWrite(LED_PIN, HIGH);
      float rssi = radio.getRSSI();
      float snr = radio.getSNR();

      Serial.println("--- Paquete Recibido ---");
      Serial.print("Datos: "); Serial.println(rxMsg);
      Serial.print("RSSI:  "); Serial.print(rssi); Serial.println(" dBm");
      Serial.print("SNR:   "); Serial.print(snr);  Serial.println(" dB");

      actualizarPantalla("RX Recibido:", rxMsg, rssi, snr);
      digitalWrite(LED_PIN, LOW);
    }
    radio.startReceive();
  }

  delay(20);
}
