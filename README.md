# 🌩️ Monitor de Alertas AEMET

Script Python que monitoriza el feed RSS de avisos meteorológicos de AEMET y notifica mediante **email HTML** y **ventanas de escritorio** cuando se detectan alertas nuevas, escaladas, reducidas o resueltas.

Desarrollado durante prácticas de ASIR como proyecto de automatización y administración de sistemas.

---

## ✨ Características

- 📡 **Parseo de RSS AEMET** (zona configurable, por defecto Madrid 722802)
- 🔴🟠🟡 **Detección de nivel**: Rojo, Naranja, Amarillo
- ⬆️⬇️ **Detección de cambios**: nuevas alertas, escaladas, reducciones y resoluciones
- 📧 **Notificación por email HTML** vía Gmail (con múltiples destinatarios desde archivo)
- 🪟 **Ventanas de escritorio** desacopladas (no bloquean futuras ejecuciones)
- 💾 **Caché atómica** con backup y limpieza automática
- 📋 **Logging rotativo** (hasta 50 MB en 5 archivos)
- 🔄 **Arquitectura Fire & Forget**: el script principal termina rápido; las ventanas viven de forma independiente
- 🐧🪟 **Cross-platform**: Windows y Linux

---

## 📁 Estructura del proyecto

```
aemet-monitor/
├── monitor_aemet.py        # Script principal
├── destinatarios.txt       # Lista de emails destinatarios (uno por línea)
├── requirements.txt        # Dependencias Python
├── env.example             # Ejemplo de variables de entorno
├── .gitignore
└── README.md
```

Archivos generados en tiempo de ejecución (no incluidos en el repo):
```
├── aemet_cache.json        # Caché de alertas activas/resueltas
├── aemet_cache.backup.json # Backup automático de la caché
└── alertas.log             # Log rotativo de ejecuciones
```

---

## ⚙️ Requisitos

- Python 3.7+
- Cuenta de Gmail con [App Password](https://myaccount.google.com/apppasswords) habilitada
- Tkinter (incluido en Python estándar; en Linux puede requerir `sudo apt install python3-tk`)

### Dependencias Python

```bash
pip install -r requirements.txt
```

---

## 🚀 Configuración y uso

### 1. Clonar el repositorio

```bash
git clone https://github.com/adrianboza2/aemet-monitor.git
cd aemet-monitor
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Copia `env.example` a `.env` y rellena tus credenciales:

```bash
cp env.example .env
```

**Variables obligatorias:**

| Variable | Descripción |
|---|---|
| `AEMET_EMAIL_FROM` | Tu dirección Gmail remitente |
| `AEMET_EMAIL_PASSWORD` | App Password de Gmail (no tu contraseña normal) |

**Variables opcionales:**

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `AEMET_RSS_URL` | Feed Madrid 722802 | URL del RSS AEMET de tu zona |
| `AEMET_EMAIL` | `True` | Habilitar notificaciones email |
| `AEMET_SOUND` | `False` | Habilitar sonido (solo Windows) |
| `AEMET_NOTIFY_DOWNGRADE` | `True` | Notificar reducciones de nivel |
| `AEMET_NOTIFY_RESOLVED` | `True` | Notificar resoluciones de alertas |

En **Linux/macOS**:
```bash
export AEMET_EMAIL_FROM="tu_email@gmail.com"
export AEMET_EMAIL_PASSWORD="xxxx xxxx xxxx xxxx"
python monitor_aemet.py
```

En **Windows (PowerShell)**:
```powershell
$env:AEMET_EMAIL_FROM="tu_email@gmail.com"
$env:AEMET_EMAIL_PASSWORD="xxxx xxxx xxxx xxxx"
python monitor_aemet.py
```

### 3. Configurar destinatarios

Edita `destinatarios.txt` con los emails que recibirán las alertas (uno por línea):

```
# Comentarios con #
admin@ejemplo.com
operaciones@ejemplo.com
```

### 4. Ejecución periódica (Task Scheduler / cron)

**Windows — Task Scheduler:**

Crea una tarea que ejecute el script cada 15–30 minutos con las variables de entorno configuradas en el sistema.

**Linux — cron:**

```bash
crontab -e
```
```cron
*/15 * * * * AEMET_EMAIL_FROM=tu@gmail.com AEMET_EMAIL_PASSWORD="xxxx xxxx xxxx xxxx" /usr/bin/python3 /ruta/monitor_aemet.py
```

---

## 🏗️ Arquitectura

```
Ejecución del script
       │
       ├─── Fetch RSS AEMET
       ├─── Comparar con caché
       ├─── Por cada alerta nueva/cambiada:
       │         ├─── Thread email (async, no bloquea)
       │         └─── Subprocess ventana (Fire & Forget)
       ├─── Guardar caché (una sola vez)
       ├─── Esperar confirmación emails (máx. 60s)
       └─── Terminar ✅
              │
              └── Procesos hijo (ventanas) siguen vivos independientemente
```

---

## 📬 Ejemplo de notificación por email

El email incluye:
- Color codificado por nivel (rojo/naranja/amarillo)
- Título y descripción del aviso
- Timestamp de la notificación
- Enlace directo a AEMET

---

## 🔧 Cómo obtener el RSS de tu zona

1. Ve a [AEMET Avisos](https://www.aemet.es/es/eltiempo/prediccion/avisos)
2. Selecciona tu comunidad/provincia
3. El código de zona aparece en la URL del RSS (ej: `CAP_AFAZ722802`)

---

## 📄 Licencia

MIT — libre para uso personal y educativo.

---

*Desarrollado por [Adrián Boza](https://github.com/adrianboza2) · Prácticas ASIR*
