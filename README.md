# Monitor de Alertas AEMET

<div align="center">

![Python](https://img.shields.io/badge/Python-3.7%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)

**Script Python que monitoriza el feed RSS de avisos meteorológicos de AEMET y notifica mediante email HTML y ventanas de escritorio cuando se detectan alertas nuevas, escaladas, reducidas o resueltas.**

</div>

---

## Descripcion

Script en Python que consulta el RSS oficial de AEMET (Agencia Estatal de Meteorologia), detecta cambios en los avisos meteorologicos y notifica automaticamente al equipo correspondiente mediante correo electronico y ventanas emergentes en el escritorio.

### Contexto Real

Este proyecto nacio durante mis practicas formativas. La empresa necesitaba monitorizar alertas meteorologicas en tiempo real para tener informacion actualizada, detallada y precisa ante condiciones adversas.

**El problema:** No existia un sistema automatizado que detectara cambios en los avisos de AEMET y notificara al equipo de operaciones de forma inmediata.

**La solucion:** Un script Python ligero con arquitectura Fire & Forget que consulta el RSS, detecta cambios y notifica automaticamente, funcionando en Windows y Linux sin modificaciones.

---

## Caracteristicas

| Caracteristica | Descripcion |
|---|---|
| Parseo de RSS AEMET | Zona configurable (por defecto Madrid 722802) |
| Deteccion de nivel | Rojo, Naranja, Amarillo |
| Deteccion de cambios | Nuevas alertas, escaladas, reducciones y resoluciones |
| Notificacion email | HTML con codigo de colores via Gmail SMTP |
| Ventanas emergentes | Procesos hijo independientes, no bloquean la ejecucion |
| Cache atomica | Backup automatico y limpieza por tiempo de retencion |
| Logging rotativo | 10 MB por archivo, hasta 5 rotaciones |
| Cross-platform | Windows y Linux |
| Configuracion segura | Variables de entorno + .env, credenciales fuera del codigo |

---

## Stack tecnologico

| Componente | Tecnologia |
|---|---|
| Lenguaje | Python 3.7+ |
| RSS Parser | feedparser 6.x |
| Email | smtplib + Gmail SMTP |
| UI Ventanas | Tkinter |
| Cache | JSON con backup atomico |
| Logging | RotatingFileHandler |
| Concurrencia | threading + subprocess |

---

## Estructura del repositorio

```
script-aemet-python/
├── monitor_aemet.py        # Script principal
├── destinatarios.txt       # Lista de emails (ignorado por git)
├── requirements.txt        # Dependencias
├── env.example             # Plantilla de variables de entorno
├── .gitignore
└── README.md
```

Archivos generados en tiempo de ejecucion:
```
├── .env                    # Configuracion local (ignorado por git)
├── aemet_cache.json        # Cache de alertas activas/resueltas
├── aemet_cache.backup.json # Backup automatico de la cache
└── alertas.log             # Log rotativo de ejecuciones
```

---

## Requisitos

- Python 3.7+
- Cuenta de Gmail con [App Password](https://myaccount.google.com/apppasswords) (opcional, solo para email)
- Tkinter (incluido en Python estandar; en Linux: `sudo apt install python3-tk`)

### Dependencias

```bash
pip install -r requirements.txt
```

---

## Configuracion y uso

### 1. Clonar

```bash
git clone https://github.com/adrianboza2/script-aemet-python.git
cd script-aemet-python
pip install -r requirements.txt
```

### 2. Configurar

**Sin email (solo ventanas emergentes):**

```powershell
# PowerShell
$env:AEMET_EMAIL="False"
python monitor_aemet.py
```

**Con email:** Copia `env.example` a `.env` y rellena tus credenciales.

### 3. Destinatarios

Edita `destinatarios.txt` (un email por linea):

```
# Comentarios con #
admin@ejemplo.com
operaciones@ejemplo.com
```

### 4. Ejecucion periodica

**Windows - Task Scheduler:** Crea una tarea cada 15-30 min.

**Linux - cron:**

```bash
crontab -e
```

```cron
*/15 * * * * /usr/bin/python3 /ruta/monitor_aemet.py
```

---

## Arquitectura

```
Ejecucion del script
       |
       +--- Fetch RSS AEMET
       +--- Comparar con cache
       +--- Por cada alerta nueva/cambiada:
       |         +--- Thread email (async, no bloquea)
       |         +--- Subprocess ventana (Fire & Forget)
       +--- Guardar cache (una sola vez)
       +--- Esperar confirmacion emails (max. 60s)
       +--- Terminar
              |
              +--- Procesos hijo (ventanas) siguen vivos independientemente
```

---

## Habilidades demostradas

| Habilidad | Implementacion |
|---|---|
| Python scripting | Logica completa del monitor, parsing, control de flujo |
| Multithreading | Envio de emails asincrono sin bloquear el proceso principal |
| Subprocess management | Ventanas desacopladas como procesos hijo independientes |
| RSS/XML parsing | Feedparser 6.x con manejo de errores y reintentos |
| SMTP / email automation | Envio de emails HTML con Gmail y App Passwords |
| Logging y persistencia | Rotacion de logs, cache JSON atomica con backup |
| Control de procesos | Gestion de procesos en Windows y Linux |
| Configuracion segura | Variables de entorno + .env, credenciales fuera del codigo |
| Cross-platform | Compatibilidad Windows/Linux probada en produccion |
| Resolucion de problemas reales | Proyecto desarrollado durante practicas formativas en un entorno empresarial real |

---

## Configurar otra zona geografica

1. Ve a [AEMET Avisos](https://www.aemet.es/es/eltiempo/prediccion/avisos)
2. Selecciona tu comunidad/provincia
3. El codigo de zona aparece en la URL del RSS (ej: `CAP_AFAZ722802`)
4. Cambialo en `.env`: `AEMET_RSS_URL=...`

---

## Licencia

MIT

---

<div align="center">
  <b>Adrian Boza</b><br>
  <a href="https://github.com/adrianboza2">GitHub</a> ·
  <a href="https://www.linkedin.com/in/adri%C3%A1n-boza-su%C3%A1rez-51623a184/">LinkedIn</a> ·
  ASIR · Cloud Security Track
  <br><br>
  <sub>Desarrollado durante practicas formativas</sub>
</div>
