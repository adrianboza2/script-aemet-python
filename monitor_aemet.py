#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor de Alertas AEMET - Windows/Linux (v5.7) - Fire & Forget
✅ ARQUITECTURA: Script principal (Rápido) + Ventanas Hijas (Independientes)
✅ Prioridad: Envío de emails y actualización de caché INMEDIATA.
✅ Las ventanas NO bloquean el script principal ni futuras ejecuciones.
✅ Destinatarios externos en destinatarios.txt
✅ Notifica downgrades, escaladas y resoluciones.
✅ Logging rotativo + reintentos + feedparser 6.x compatible.
✅ Cross-platform: Windows + Linux
"""

from dotenv import load_dotenv
import feedparser
import smtplib
import json
import os
import sys
import threading
import tkinter as tk
import hashlib
import re
import logging
import logging.handlers
import time
import shutil
import socket
import subprocess
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from pathlib import Path
import webbrowser

# ==========================================
# ⚙️ CONFIGURACIÓN
# ==========================================
load_dotenv()

BASE_DIR = Path(__file__).parent.resolve()
CACHE_FILE = BASE_DIR / "aemet_cache.json"
CACHE_BACKUP = BASE_DIR / "aemet_cache.backup.json"
LOG_FILE = BASE_DIR / "alertas.log"
DEST_FILE = BASE_DIR / "destinatarios.txt"

RSS_URL = os.getenv(
    "AEMET_RSS_URL",
    "https://www.aemet.es/documentos_d/eltiempo/prediccion/avisos/rss/CAP_AFAZ722802_RSS.xml"
)
ACTIVAR_SONIDO = os.getenv("AEMET_SOUND", "False").lower() == "true"
ENVIAR_EMAIL = os.getenv("AEMET_EMAIL", "True").lower() == "true"
NOTIFICAR_DOWNGRADES = os.getenv("AEMET_NOTIFY_DOWNGRADE", "True").lower() == "true"
NOTIFICAR_RESOLUCION = os.getenv("AEMET_NOTIFY_RESOLVED", "True").lower() == "true"

# Credenciales (solo obligatorias si el email está habilitado)
EMAIL_DE = os.getenv("AEMET_EMAIL_FROM")
CLAVE_APP_GMAIL = os.getenv("AEMET_EMAIL_PASSWORD")

if ENVIAR_EMAIL:
    if not EMAIL_DE:
        print("❌ ERROR: AEMET_EMAIL=True pero AEMET_EMAIL_FROM no está configurado")
        print("   Ejemplo: export AEMET_EMAIL_FROM='tu_email@gmail.com'")
        sys.exit(1)
    if not CLAVE_APP_GMAIL:
        print("❌ ERROR: AEMET_EMAIL=True pero AEMET_EMAIL_PASSWORD no está configurado")
        print("   Usa una App Password de Gmail: https://myaccount.google.com/apppasswords")
        sys.exit(1)

CACHE_MAX_ENTRADAS = 500
CACHE_DIAS_RETENCION = 30
CACHE_DIAS_RETENCION_RESUELTAS = 7

PRIORIDAD_NIVEL = {"AMARILLO": 1, "NARANJA": 2, "ROJO": 3}

# Solo importar winsound en Windows
try:
    import winsound
    WINSOUND_DISPONIBLE = True
except ImportError:
    WINSOUND_DISPONIBLE = False

# ==========================================
# 📋 LOGGING (se configura antes de cargar destinatarios)
# ==========================================
logger = logging.getLogger(__name__)

def configurar_logging():
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8'
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

configurar_logging()

# ==========================================
# 📧 CARGA DE DESTINATARIOS DESDE ARCHIVO
# ==========================================
def cargar_destinatarios(ruta_archivo: Path) -> list:
    """Carga destinatarios desde archivo de texto (uno por línea, # para comentarios)."""
    lista = []
    try:
        if not ruta_archivo.exists():
            logger.warning(f"⚠️ Archivo no encontrado: {ruta_archivo}. Usando fallback.")
            return [EMAIL_DE]

        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            for num_linea, linea in enumerate(f, 1):
                email = linea.strip()
                if not email or email.startswith('#'):
                    continue
                if '@' in email and '.' in email.split('@')[-1]:
                    lista.append(email)
                else:
                    logger.warning(f"⚠️ Email inválido en línea {num_linea}: '{email}'")

        if not lista:
            logger.warning("⚠️ destinatarios.txt vacío. Usando fallback.")
            return [EMAIL_DE]

        logger.info(f"📧 {len(lista)} destinatarios cargados desde {ruta_archivo.name}")
        return lista

    except Exception as e:
        logger.error(f"❌ Error leyendo destinatarios: {e}. Usando fallback.")
        return [EMAIL_DE]

# Carga inicial de destinatarios
DESTINATARIOS = cargar_destinatarios(DEST_FILE)
EMAIL_PARA = ", ".join(DESTINATARIOS)

# ==========================================
# 💾 CACHÉ
# ==========================================
def _parsear_datetime(ts: str) -> datetime:
    """Parsea un timestamp ISO 8601 de forma robusta (compatible con Python 3.6+)."""
    if not ts:
        return datetime.now()
    # Normalizar: quitar la Z o el +00:00 duplicado
    ts = ts.strip()
    if ts.endswith('Z'):
        ts = ts[:-1] + '+00:00'
    try:
        # Python 3.7+ soporta fromisoformat con offset
        dt = datetime.fromisoformat(ts)
        # Convertir a naive UTC para comparaciones uniformes
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except ValueError:
        logger.warning(f"⚠️ Timestamp no parseable: '{ts}'. Usando ahora.")
        return datetime.now()

def cargar_cache() -> dict:
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"⚠️ Caché corrupta ({e}), restaurando backup...")
        if CACHE_BACKUP.exists():
            try:
                with open(CACHE_BACKUP, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

def guardar_cache_atomico(cache: dict) -> None:
    try:
        if CACHE_FILE.exists():
            shutil.copy2(CACHE_FILE, CACHE_BACKUP)
        cache_limpia = _limpiar_cache(cache)
        tmp = CACHE_FILE.with_suffix('.tmp')
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(cache_limpia, f, ensure_ascii=False, indent=2)
        tmp.replace(CACHE_FILE)
    except Exception as e:
        logger.error(f"❌ Error guardando caché: {e}")

def _limpiar_cache(cache: dict) -> dict:
    if not cache:
        return cache
    ahora = datetime.now()
    limpia = {}
    for k, v in cache.items():
        if not isinstance(v, dict):
            v = {"nivel": "DESCONOCIDO", "timestamp": ahora.isoformat(), "estado": "activa"}
        try:
            if v.get("estado") == "resuelta":
                ts_ref = v.get("timestamp_resolucion") or v.get("timestamp", "")
                dias_retencion = CACHE_DIAS_RETENCION_RESUELTAS
            else:
                ts_ref = v.get("timestamp", "")
                dias_retencion = CACHE_DIAS_RETENCION

            fecha_ref = _parsear_datetime(ts_ref)
            if (ahora - fecha_ref).days <= dias_retencion:
                limpia[k] = v
        except Exception:
            pass  # Entrada corrupta: descartada

    if len(limpia) > CACHE_MAX_ENTRADAS:
        try:
            ordenadas = sorted(
                limpia.items(),
                key=lambda x: x[1].get("timestamp", "1970"),
                reverse=True
            )[:CACHE_MAX_ENTRADAS]
            return dict(ordenadas)
        except Exception:
            pass
    return limpia

def generar_id(entry) -> str:
    guid = entry.get("guid")
    if guid and isinstance(guid, str) and guid.strip():
        return guid.strip()
    contenido = f"{entry.get('title','')}|{entry.get('description','')}|{entry.get('published','')}"
    return hashlib.sha256(contenido.encode('utf-8')).hexdigest()

# ==========================================
# 🌐 RSS
# ==========================================
def fetch_rss(url: str, timeout: int = 10, reintentos: int = 3, espera: int = 5):
    """Compatible con feedparser 6.x: usa socket timeout global."""
    old_timeout = socket.getdefaulttimeout()
    for i in range(1, reintentos + 1):
        try:
            socket.setdefaulttimeout(timeout)
            feed = feedparser.parse(url)
            socket.setdefaulttimeout(old_timeout)
            if feed.entries:
                return feed
            logger.warning(f"⚠️ RSS vacío (intento {i}/{reintentos})")
        except Exception as e:
            socket.setdefaulttimeout(old_timeout)
            logger.error(f"❌ Error feedparser (intento {i}): {e}")
        if i < reintentos:
            time.sleep(espera)
    socket.setdefaulttimeout(old_timeout)
    return None

# ==========================================
# 🔧 UTILS
# ==========================================
def utf8(texto) -> str:
    if texto is None:
        return ""
    return str(texto, 'utf-8', errors='replace') if isinstance(texto, bytes) else str(texto)

def obtener_nivel(titulo: str) -> str:
    if not titulo:
        return "NARANJA"
    t = titulo.lower()
    if re.search(r'nivel\s+rojo|rojo.*aviso|aviso.*rojo', t):
        return "ROJO"
    if re.search(r'nivel\s+naranja|naranja.*aviso|aviso.*naranja', t):
        return "NARANJA"
    if re.search(r'nivel\s+amarillo|amarillo.*aviso|aviso.*amarillo', t):
        return "AMARILLO"
    logger.warning(f"⚠️ Nivel no detectado en: '{titulo[:60]}'. Asignando NARANJA.")
    return "NARANJA"

def detectar_cambio_nivel(nivel_nuevo: str, nivel_anterior: str = None) -> str:
    if nivel_anterior is None:
        return "NUEVA"
    p_nuevo = PRIORIDAD_NIVEL.get(nivel_nuevo, 0)
    p_anterior = PRIORIDAD_NIVEL.get(nivel_anterior, 0)
    if p_nuevo > p_anterior:
        return "ESCALADA"
    elif p_nuevo < p_anterior:
        return "REDUCCION"
    else:
        return "SIN_CAMBIO"

# ==========================================
# 📧 EMAIL (Async)
# ==========================================
ESTILOS_EMAIL = {
    "ROJO":     {"color": "#d32f2f", "fondo": "#ffebee", "emoji": "🔴"},
    "NARANJA":  {"color": "#f57c00", "fondo": "#fff3e0", "emoji": "🟠"},
    "AMARILLO": {"color": "#fbc02d", "fondo": "#fffde7", "emoji": "🟡"},
    "ESCALADA": {"color": "#d32f2f", "fondo": "#ffebee", "emoji": "⬆️"},
    "REDUCCION":{"color": "#388e3c", "fondo": "#e8f5e9", "emoji": "⬇️"},
    "RESUELTA": {"color": "#388e3c", "fondo": "#e8f5e9", "emoji": "✅"},
}

def validar_email() -> bool:
    if not ENVIAR_EMAIL:
        return False
    try:
        s = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        s.starttls()
        s.login(EMAIL_DE, CLAVE_APP_GMAIL)
        s.quit()
        logger.info("✅ Conexión email verificada.")
        return True
    except Exception as e:
        logger.error(f"❌ Fallo validación email: {e}")
        return False

def _enviar_email_worker(nivel: str, titulo: str, descripcion: str, enlace: str,
                         evento_completado: threading.Event, tipo_cambio: str = "NUEVA") -> None:
    est = ESTILOS_EMAIL.get(tipo_cambio) or ESTILOS_EMAIL.get(nivel, ESTILOS_EMAIL["NARANJA"])

    if tipo_cambio == "RESUELTA":
        titulo_html = "✅ ALERTA FINALIZADA"
        cuerpo_extra = "<p style='color:#388e3c;font-weight:bold'>La alerta ha sido cancelada.</p>"
    elif tipo_cambio == "REDUCCION":
        titulo_html = f"⬇️ Reducción a {nivel}"
        cuerpo_extra = "<p style='color:#388e3c'>Severidad reducida.</p>"
    elif tipo_cambio == "ESCALADA":
        titulo_html = f"⬆️ Escalada a {nivel}"
        cuerpo_extra = "<p style='color:#d32f2f;font-weight:bold'>Severidad aumentada.</p>"
    else:
        titulo_html = f"{est['emoji']} AEMET — Aviso {nivel}"
        cuerpo_extra = ""

    html = f"""<html><body style="font-family:sans-serif;background:{est['fondo']};padding:20px;">
<div style="background:white;padding:20px;border-left:5px solid {est['color']};border-radius:8px;">
 <h2 style="color:{est['color']}">{titulo_html}</h2>
 <h3>{utf8(titulo)}</h3>
 {cuerpo_extra}
 <p>{utf8(descripcion)}</p>
 <hr><p style="font-size:12px;color:#888">{datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
 <a href="{enlace}" style="background:{est['color']};color:white;padding:10px 20px;text-decoration:none;border-radius:4px;font-weight:bold;">Ver en AEMET →</a>
</div></body></html>"""

    enviado = False
    for intento in range(1, 3):
        try:
            msg = MIMEMultipart('alternative')
            emoji = est.get("emoji", "")
            msg['Subject'] = f"{emoji} AEMET {tipo_cambio}: {utf8(titulo)}"
            msg['From'] = EMAIL_DE
            msg['To'] = EMAIL_PARA
            msg.attach(MIMEText(html, 'html', 'utf-8'))
            s = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
            s.starttls()
            s.login(EMAIL_DE, CLAVE_APP_GMAIL)
            s.send_message(msg)
            s.quit()
            logger.info(f"📧 Email enviado a {len(DESTINATARIOS)} dest. [{tipo_cambio}]")
            enviado = True
            break
        except Exception as e:
            logger.warning(f"⚠️ Fallo email intento {intento}/2: {e}")
            if intento < 2:
                time.sleep(10)

    if not enviado:
        logger.error(f"❌ Email no enviado [{tipo_cambio}]")
    evento_completado.set()

def disparar_email_async(nivel, titulo, descripcion, enlace, tipo_cambio="NUEVA") -> threading.Event:
    evento = threading.Event()
    threading.Thread(
        target=_enviar_email_worker,
        args=(nivel, titulo, descripcion, enlace, evento, tipo_cambio),
        daemon=False
    ).start()
    return evento

# ==========================================
# 🪟 VENTANA (Modo Hijo - Desacoplado)
# ==========================================
ESTILOS_VENTANA = {
    "ROJO":     {"bg": "#ffcccc", "fg": "#8b0000", "btn": "#d32f2f", "tit": "🔴 ALERTA CRÍTICA"},
    "NARANJA":  {"bg": "#ffe0b2", "fg": "#e65100", "btn": "#f57c00", "tit": "🟠 AVISO IMPORTANTE"},
    "AMARILLO": {"bg": "#fff9c4", "fg": "#f57f17", "btn": "#fbc02d", "tit": "🟡 AVISO"},
    "ESCALADA": {"bg": "#ffcccc", "fg": "#8b0000", "btn": "#d32f2f", "tit": "⬆️ ESCALADA"},
    "REDUCCION":{"bg": "#c8e6c9", "fg": "#1b5e20", "btn": "#388e3c", "tit": "⬇️ REDUCCIÓN"},
    "RESUELTA": {"bg": "#c8e6c9", "fg": "#1b5e20", "btn": "#388e3c", "tit": "✅ FINALIZADA"},
}

def lanzar_ventana_remota(alerta_data: dict) -> None:
    """Lanza una nueva instancia de Python en segundo plano para mostrar la ventana."""
    try:
        script_path = str(Path(__file__).resolve())
        data_json = json.dumps(alerta_data, ensure_ascii=False)

        cmd = [sys.executable, script_path, "--show-alert", data_json]

        if sys.platform == "win32":
            subprocess.Popen(
                cmd,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            subprocess.Popen(cmd, start_new_session=True)

        logger.debug(f"🪟 Ventana lanzada en segundo plano: {alerta_data['titulo'][:30]}")
    except Exception as e:
        logger.error(f"❌ Error lanzando ventana remota: {e}")

def ejecutar_ventana_ui(datos: dict) -> None:
    """Lógica exclusiva de la interfaz gráfica (ejecutada por el proceso hijo)."""
    tipo_cambio = datos.get("tipo_cambio", "NUEVA")
    nivel = datos.get("nivel", "NARANJA")
    titulo = datos.get("titulo", "")
    descripcion = datos.get("descripcion", "")
    enlace = datos.get("enlace", "")

    if ACTIVAR_SONIDO and WINSOUND_DISPONIBLE:
        try:
            beep = winsound.MB_ICONINFORMATION if tipo_cambio == "RESUELTA" else winsound.MB_ICONEXCLAMATION
            winsound.MessageBeep(beep)
        except Exception:
            pass

    est = ESTILOS_VENTANA.get(tipo_cambio) or ESTILOS_VENTANA.get(nivel, ESTILOS_VENTANA["NARANJA"])

    if tipo_cambio == "RESUELTA":
        texto_titulo = f"✅ La alerta ha finalizado:\n{utf8(titulo)}"
    elif tipo_cambio == "REDUCCION":
        texto_titulo = f"⬇️ Severidad reducida a {nivel}:\n{utf8(titulo)}"
    elif tipo_cambio == "ESCALADA":
        texto_titulo = f"⬆️ Severidad aumentada a {nivel}:\n{utf8(titulo)}"
    else:
        texto_titulo = utf8(titulo)

    root = tk.Tk()
    root.title(f"{est['tit']} — AEMET")
    w, h = 560, 420
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.configure(bg=est["bg"])
    root.attributes("-topmost", True)

    def cerrar():
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", cerrar)

    tk.Label(
        root, text=texto_titulo,
        font=("Arial", 15, "bold"), bg=est["bg"], fg=est["fg"],
        wraplength=520, justify="center"
    ).pack(pady=(25, 10))

    tk.Label(
        root, text=utf8(descripcion),
        font=("Arial", 11), bg=est["bg"], fg="#333",
        wraplength=520, justify="center"
    ).pack(pady=5, padx=20)

    if enlace and tipo_cambio != "RESUELTA":
        tk.Button(
            root, text="🔗 Ver en AEMET", bg="white",
            command=lambda: webbrowser.open(enlace),
            font=("Arial", 10, "bold"), cursor="hand2"
        ).pack(pady=12)

    tk.Button(
        root, text="✅ ENTENDIDO — CERRAR", bg=est["btn"], fg="white",
        command=cerrar, font=("Arial", 13, "bold"),
        padx=30, pady=12, cursor="hand2"
    ).pack(pady=15)

    root.mainloop()

# ==========================================
# 🧠 MAIN (Lógica de Monitor)
# ==========================================
def main():
    logger.info("=" * 60)
    logger.info("🚀 Iniciando Monitor AEMET v5.7 (Fire & Forget)")

    # Recargar destinatarios en cada ejecución
    global DESTINATARIOS, EMAIL_PARA
    DESTINATARIOS = cargar_destinatarios(DEST_FILE)
    EMAIL_PARA = ", ".join(DESTINATARIOS)

    email_activo = validar_email()
    if ENVIAR_EMAIL and not email_activo:
        logger.warning("⚠️ Email deshabilitado por fallo de configuración.")

    cache = cargar_cache()
    feed = fetch_rss(RSS_URL)
    if not feed:
        logger.error("❌ No se pudo obtener RSS. Abortando.")
        return

    nuevas_alertas = []
    uids_en_feed = set()

    for entry in feed.entries:
        titulo = utf8(entry.get("title", ""))
        link = str(entry.get("link", ""))
        if "no hay avisos" in titulo.lower() or link.lower().endswith(".tar.gz"):
            continue

        nivel = obtener_nivel(titulo)
        uid = generar_id(entry)
        uids_en_feed.add(uid)

        en_cache = cache.get(uid)
        nivel_anterior = en_cache.get("nivel") if en_cache else None
        tipo_cambio = detectar_cambio_nivel(nivel, nivel_anterior)

        notificar = False
        if tipo_cambio == "NUEVA":
            notificar = True
        elif tipo_cambio == "ESCALADA":
            notificar = True
        elif tipo_cambio == "REDUCCION" and NOTIFICAR_DOWNGRADES:
            notificar = True

        if notificar:
            nuevas_alertas.append({
                "uid": uid, "nivel": nivel, "titulo": titulo,
                "descripcion": utf8(entry.get("description", "")),
                "enlace": link, "tipo_cambio": tipo_cambio
            })

    # Detectar resoluciones (alertas que desaparecieron del feed)
    if NOTIFICAR_RESOLUCION:
        for uid_cache, datos_cache in cache.items():
            if datos_cache.get("estado") == "resuelta":
                continue
            if uid_cache not in uids_en_feed:
                logger.info(f" → Alerta resuelta (desapareció): {datos_cache.get('titulo', 'N/A')[:50]}")
                nuevas_alertas.append({
                    "uid": uid_cache,
                    "nivel": datos_cache.get("nivel", "DESCONOCIDO"),
                    "titulo": datos_cache.get("titulo", "Alerta finalizada"),
                    "descripcion": "✅ Alerta cancelada o expirada según AEMET.",
                    "enlace": RSS_URL,
                    "tipo_cambio": "RESUELTA",
                    "es_resolucion": True
                })

    if not nuevas_alertas:
        logger.info("✅ Sin novedades. Finalizando.")
        return

    logger.info(f"🚨 {len(nuevas_alertas)} alerta(s) a procesar.")

    # 🔄 BUCLE DE PROCESAMIENTO
    eventos_email = []

    for alerta in nuevas_alertas:
        nivel = alerta["nivel"]
        titulo = alerta["titulo"]
        descripcion = alerta["descripcion"]
        enlace = alerta["enlace"]
        uid = alerta["uid"]
        tipo_cambio = alerta.get("tipo_cambio", "NUEVA")
        es_resolucion = alerta.get("es_resolucion", False)

        # 1. Disparar Email (Async — No bloquea)
        if email_activo:
            evento = disparar_email_async(nivel, titulo, descripcion, enlace, tipo_cambio)
            eventos_email.append(evento)

        # 2. Actualizar Caché
        if es_resolucion:
            cache[uid] = {
                "nivel": nivel,
                "titulo": titulo,
                "timestamp": cache.get(uid, {}).get("timestamp", datetime.now().isoformat()),
                "timestamp_resolucion": datetime.now().isoformat(),
                "estado": "resuelta"
            }
        else:
            cache[uid] = {
                "nivel": nivel,
                "titulo": titulo,
                "timestamp": datetime.now().isoformat(),
                "estado": "activa"
            }

        # 3. Lanzar Ventana (Fire & Forget)
        lanzar_ventana_remota(alerta)

    # 4. Guardar caché UNA sola vez al finalizar el bucle (más eficiente)
    guardar_cache_atomico(cache)
    logger.info("💾 Caché guardada.")

    # 5. Esperar a que todos los emails terminen (máx. 60 s)
    if eventos_email:
        logger.info(f"⏳ Esperando {len(eventos_email)} email(s)...")
        for evento in eventos_email:
            evento.wait(timeout=60)

    logger.info("✅ Monitor AEMET finalizado correctamente (Ventanas en segundo plano).")
    logger.info("=" * 60)


if __name__ == "__main__":
    if "--show-alert" in sys.argv:
        # Modo Hijo: solo ejecuta la UI con los datos recibidos por argumento
        try:
            # Usar sys.argv[2] en adelante y reunir en caso de que el shell haya dividido el JSON
            datos_json = " ".join(sys.argv[2:])
            datos_alerta = json.loads(datos_json)
            ejecutar_ventana_ui(datos_alerta)
        except Exception as e:
            print(f"Error en modo UI: {e}")
        sys.exit(0)
    else:
        # Modo Padre: ejecuta el monitor completo
        main()
