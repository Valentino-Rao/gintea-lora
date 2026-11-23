#!/usr/bin/env python3
"""
GINTEA - Herramienta de terminal para la estación TinyGS (Heltec WiFi LoRa 32 V3).

Subcomandos:
  puertos     Lista los puertos serie y marca la placa (CP2102, 10C4:EA60).
  descargar   Baja el firmware oficial de TinyGS para ESP32-S3 y verifica su SHA-256.
  flashear    Borra la flash y graba TinyGS (pide confirmación: borra la configuración).
  monitor     Reinicia la placa y muestra su salida serie (oculta contraseñas).
  comando     Envía un comando de consola de TinyGS (reiniciar, borrar-config, otp, ...).

Ejemplos:
  python scripts/tinygs.py puertos
  python scripts/tinygs.py flashear
  python scripts/tinygs.py monitor --segundos 60
  python scripts/tinygs.py comando otp

Requiere: pip install -r scripts/requirements.txt  (pyserial y esptool)
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO_TINYGS = "tinygs/tinyGS"
CHIP = "esp32s3"
BAUD_SERIE = 115200
BAUD_FLASH = 921600
VID_PID_PLACA = (0x10C4, 0xEA60)  # CP2102 de la Heltec V3
CARPETA_FIRMWARE = Path(__file__).resolve().parent / "firmware"

# Comandos de la consola serie de TinyGS ("!<letra>").
COMANDOS = {
    "reiniciar": ("b", "Reinicia la placa."),
    "borrar-config": ("e", "Borra TODA la configuración (WiFi, MQTT, nombre) y reinicia."),
    "otp": ("o", "Muestra el código OTP para registrar la estación."),
    "weblogin": ("w", "Pide un link de acceso al panel web (no lo compartas)."),
    "paquete-prueba": ("p", "Transmite un paquete de prueba (solo si TX está habilitado)."),
}

# Líneas con estas palabras se muestran con el valor oculto.
PATRON_SENSIBLE = re.compile(r"(?i)(pass|pw\b|token|mqtt.?user)")


def salir(mensaje, codigo=1):
    print(f"ERROR: {mensaje}", file=sys.stderr)
    sys.exit(codigo)


def importar_serial():
    try:
        import serial  # noqa: F401
        import serial.tools.list_ports  # noqa: F401
    except ImportError:
        salir("falta pyserial. Instalalo con: pip install -r scripts/requirements.txt")
    import serial
    return serial


# ----------------------------------------------------------------- puertos ---

def buscar_puertos():
    serial = importar_serial()
    puertos = list(serial.tools.list_ports.comports())
    placas = [p for p in puertos if (p.vid, p.pid) == VID_PID_PLACA]
    return puertos, placas


def elegir_puerto(puerto):
    if puerto:
        return puerto
    _, placas = buscar_puertos()
    if not placas:
        salir("no encontré la placa (CP2102 10C4:EA60). Revisá el cable USB-C "
              "(que pase datos) o indicá el puerto con --puerto.")
    if len(placas) > 1:
        lista = ", ".join(p.device for p in placas)
        salir(f"hay varias placas conectadas ({lista}). Elegí una con --puerto.")
    return placas[0].device


def cmd_puertos(_args):
    puertos, _ = buscar_puertos()
    if not puertos:
        print("No hay puertos serie disponibles.")
        return
    for p in puertos:
        marca = "  <-- Heltec V3 (CP2102)" if (p.vid, p.pid) == VID_PID_PLACA else ""
        print(f"{p.device:15s} {p.description}{marca}")


# --------------------------------------------------------------- descargar ---

def pedir_json(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "gintea-tinygs-script"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def sha256_de(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 16), b""):
            h.update(bloque)
    return h.hexdigest()


def descargar_firmware(version=None):
    """Devuelve la ruta al binario completo (full.bin) de TinyGS para ESP32-S3."""
    if version:
        url = f"https://api.github.com/repos/{REPO_TINYGS}/releases/tags/{version}"
    else:
        url = f"https://api.github.com/repos/{REPO_TINYGS}/releases/latest"
    try:
        release = pedir_json(url)
    except Exception as e:  # sin red, versión inexistente, límite de la API...
        salir(f"no pude consultar la release de TinyGS ({e}).")

    tag = release["tag_name"]
    nombre = f"tinygs-ESP32-S3-{tag}-full.bin"
    asset = next((a for a in release.get("assets", []) if a["name"] == nombre), None)
    if asset is None:
        salir(f"la release {tag} no tiene el archivo {nombre}.")

    esperado = (asset.get("digest") or "").removeprefix("sha256:") or None
    CARPETA_FIRMWARE.mkdir(exist_ok=True)
    destino = CARPETA_FIRMWARE / nombre

    if destino.exists() and esperado and sha256_de(destino) == esperado:
        print(f"Firmware {tag} ya descargado y verificado: {destino}")
        return destino

    print(f"Descargando TinyGS {tag} ({asset['size'] / 1e6:.1f} MB) desde GitHub...")
    temporal = destino.with_suffix(".part")
    urllib.request.urlretrieve(asset["browser_download_url"], temporal)
    obtenido = sha256_de(temporal)
    if esperado and obtenido != esperado:
        temporal.unlink()
        salir(f"el SHA-256 no coincide (esperado {esperado}, obtenido {obtenido}).")
    temporal.replace(destino)
    estado = "verificado contra GitHub" if esperado else "SIN verificar (GitHub no publicó el hash)"
    print(f"Listo: {destino}  [SHA-256 {estado}]")
    return destino


def cmd_descargar(args):
    descargar_firmware(args.version)


# ---------------------------------------------------------------- flashear ---

def correr_esptool(*argumentos):
    comando = [sys.executable, "-m", "esptool", *argumentos]
    print("$ " + " ".join(comando[2:]))
    if subprocess.call(comando) != 0:
        salir("esptool terminó con error. ¿Está bien el puerto? Si sigue fallando, mantené "
              "apretado PRG, tocá RST, soltá PRG y volvé a intentar.")


def cmd_flashear(args):
    try:
        import esptool  # noqa: F401
    except ImportError:
        salir("falta esptool. Instalalo con: pip install -r scripts/requirements.txt")

    firmware = descargar_firmware(args.version)
    puerto = elegir_puerto(args.puerto)

    print(f"\nSe va a BORRAR toda la flash de la placa en {puerto} y grabar {firmware.name}.")
    print("Esto elimina la configuración guardada (WiFi, MQTT, nombre de la estación).")
    if not args.si and input("¿Continuar? [s/N] ").strip().lower() not in ("s", "si", "sí"):
        print("Cancelado.")
        return

    correr_esptool("--chip", CHIP, "-p", puerto, "-b", str(BAUD_FLASH), "erase_flash")
    correr_esptool("--chip", CHIP, "-p", puerto, "-b", str(BAUD_FLASH),
                   "write_flash", "0x0", str(firmware))
    print("\nTinyGS grabado. La placa va a levantar la red WiFi abierta \"My TinyGS\":")
    print("conectate y entrá a http://192.168.4.1 para configurarla (ver README).")


# ----------------------------------------------------------------- monitor ---

def abrir_placa(puerto, reiniciar=True):
    """Abre el puerto. En la Heltec V3, RTS maneja EN (reset) y DTR maneja IO0 (boot)."""
    serial = importar_serial()
    s = serial.Serial()
    s.port, s.baudrate, s.timeout = puerto, BAUD_SERIE, 0.2
    s.dtr = False  # IO0 en alto: arranca el firmware, no el bootloader
    s.rts = False
    try:
        s.open()
    except serial.SerialException as e:
        salir(f"no pude abrir {puerto} ({e}). ¿Lo está usando otro programa?")
    if reiniciar:
        s.rts = True
        time.sleep(0.15)
        s.rts = False
    return s


def ocultar(linea):
    if PATRON_SENSIBLE.search(linea):
        return re.sub(r"(:\s*).+", r"\1[oculto]", linea)
    return linea


class LectorLineas:
    def __init__(self, puerto_serie, mostrar_todo=False):
        self.s = puerto_serie
        self.mostrar_todo = mostrar_todo
        self.resto = b""

    def leer(self):
        """Devuelve las líneas completas recibidas y las imprime."""
        self.resto += self.s.read(4096)
        *lineas, self.resto = self.resto.split(b"\n")
        textos = []
        for cruda in lineas:
            texto = cruda.decode("utf-8", "replace").rstrip("\r")
            textos.append(texto)
            print(texto if self.mostrar_todo else ocultar(texto), flush=True)
        return textos


def cmd_monitor(args):
    puerto = elegir_puerto(args.puerto)
    s = abrir_placa(puerto, reiniciar=not args.sin_reiniciar)
    print(f"--- Monitor de {puerto} a {BAUD_SERIE} baudios (Ctrl+C para salir) ---", flush=True)
    lector = LectorLineas(s, args.mostrar_todo)
    fin = time.time() + args.segundos if args.segundos else None
    try:
        while fin is None or time.time() < fin:
            lector.leer()
    except KeyboardInterrupt:
        pass
    finally:
        s.close()


# ----------------------------------------------------------------- comando ---

def cmd_comando(args):
    letra, _ = COMANDOS[args.nombre]
    puerto = elegir_puerto(args.puerto)
    s = abrir_placa(puerto)  # abrir el puerto reinicia la placa: esperamos que arranque
    lector = LectorLineas(s, mostrar_todo=args.nombre == "weblogin")
    print("Esperando que arranque TinyGS...", flush=True)
    limite = time.time() + 20
    listo = False
    while time.time() < limite and not listo:
        listo = any("Controls" in t for t in lector.leer())
    if not listo:
        s.close()
        salir("TinyGS no respondió en 20 s. ¿Tiene TinyGS grabado?")
    time.sleep(1)
    print(f">>> enviando !{letra} ({args.nombre})", flush=True)
    s.write(f"!{letra}\n".encode())
    fin = time.time() + args.segundos
    try:
        while time.time() < fin:
            lector.leer()
    except KeyboardInterrupt:
        pass
    finally:
        s.close()


# -------------------------------------------------------------------- main ---

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    p = argparse.ArgumentParser(description="Herramientas TinyGS para la Heltec V3 (GINTEA).")
    sub = p.add_subparsers(dest="subcomando", required=True)

    sub.add_parser("puertos", help="lista los puertos serie y marca la placa").set_defaults(f=cmd_puertos)

    d = sub.add_parser("descargar", help="descarga y verifica el firmware de TinyGS")
    d.add_argument("--version", help="tag de la release (por defecto, la última)")
    d.set_defaults(f=cmd_descargar)

    f = sub.add_parser("flashear", help="borra la placa y graba TinyGS")
    f.add_argument("--puerto", help="puerto serie (por defecto se detecta solo)")
    f.add_argument("--version", help="tag de la release (por defecto, la última)")
    f.add_argument("--si", action="store_true", help="no pedir confirmación")
    f.set_defaults(f=cmd_flashear)

    m = sub.add_parser("monitor", help="muestra la salida serie de la placa")
    m.add_argument("--puerto", help="puerto serie (por defecto se detecta solo)")
    m.add_argument("--segundos", type=float, default=0, help="cortar después de N segundos (0 = hasta Ctrl+C)")
    m.add_argument("--sin-reiniciar", action="store_true", help="no forzar un reinicio al abrir")
    m.add_argument("--mostrar-todo", action="store_true", help="no ocultar contraseñas")
    m.set_defaults(f=cmd_monitor)

    c = sub.add_parser("comando", help="envía un comando de consola a TinyGS",
                       description="\n".join(f"  {k:15s} {v[1]}" for k, v in COMANDOS.items()),
                       formatter_class=argparse.RawDescriptionHelpFormatter)
    c.add_argument("nombre", choices=COMANDOS)
    c.add_argument("--puerto", help="puerto serie (por defecto se detecta solo)")
    c.add_argument("--segundos", type=float, default=10, help="segundos a mostrar la respuesta")
    c.set_defaults(f=cmd_comando)

    args = p.parse_args()
    args.f(args)


if __name__ == "__main__":
    main()
