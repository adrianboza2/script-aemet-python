<div align="center">

# 🌩️ Monitor de avisos meteorológicos

**Vigila los avisos oficiales de AEMET y avisa al equipo de operaciones en cuanto uno aparece, empeora, baja o se resuelve.**

![Python](https://img.shields.io/badge/Python-3.7%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-0078D6?style=flat-square&logo=windows&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=flat-square&logo=linux&logoColor=black)
![Used in production](https://img.shields.io/badge/en_producción-3fb950?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square)

<sub><a href="README.md">🇬🇧 English</a> · 🇪🇸 Español</sub>

</div>

<table>
<tr>
<td align="center" width="33%"><img src="img/alertasubida.jpg" alt="Ventana: aviso escalado a naranja"><br><sub>⬆️ Sube de nivel</sub></td>
<td align="center" width="33%"><img src="img/alertaroja.png" alt="Ventana: aviso rojo"><br><sub>🔴 Crítico</sub></td>
<td align="center" width="33%"><img src="img/alertabajada.jpg" alt="Ventana: aviso rebajado a amarillo"><br><sub>⬇️ Baja de nivel</sub></td>
</tr>
</table>

## 🏭 Por qué existe

En mis prácticas la empresa necesitaba información al día sobre el mal tiempo, pero no había nada automático que siguiera los avisos de AEMET. Lo escribí para que el equipo reciba un **email y una ventana en pantalla** a los pocos minutos de que AEMET publique o cambie un aviso de su zona. Allí corría en Windows; el mismo código funciona sin cambios en Linux.

## 💡 Por qué es sólido

- **Detecta cambios, no spamea** — solo avisa de avisos *nuevos*, que *suben*, *bajan* o *se resuelven*, cada uno con su color.
- **Nunca se queda colgado** — los emails salen en otro hilo y las ventanas son procesos aparte, así que cada ejecución programada termina.
- **Estado a prueba de cortes** — escritura atómica de la caché con copia automática, y limpieza de lo antiguo.
- **Aguanta una red inestable** — lectura del RSS con timeout y reintentos.
- **Los secretos fuera del código** — App Password de Gmail en variables de entorno / `.env`; logs rotativos (10 MB × 5).

## 🔁 Cómo funciona

```mermaid
flowchart LR
    cron([cron / Task Scheduler<br/>cada 15 min]) --> fetch[Leer el RSS<br/>de AEMET]
    fetch --> diff{Comparar con<br/>la caché}
    diff -->|nuevo · sube ·<br/>baja · resuelto| notify
    diff -->|sin cambios| done([fin])
    subgraph notify[Avisar — sin bloquear]
        mail[Email HTML<br/>en otro hilo]
        pop[Ventana emergente<br/>proceso aparte]
    end
    notify --> cache[(Caché atómica<br/>+ copia)]
    cache --> done
```

## 🚀 Arranque rápido

```bash
pip install -r requirements.txt
AEMET_EMAIL=False python monitor_aemet.py      # solo ventanas, sin configurar email
```

Para el email, copia `env.example` a `.env`, pon una App Password de Gmail y los destinatarios en `destinatarios.txt`. Después prográmalo cada 15 minutos:

```cron
*/15 * * * * /usr/bin/python3 /ruta/a/monitor_aemet.py
```

Vale para cualquier zona de España: cambia `AEMET_RSS_URL` por el feed de la tuya.

---

<sub>📄 Documentación completa (configuración, arquitectura, todas las opciones) en [`docs/DETALLES.md`](docs/DETALLES.md). Licencia MIT.</sub>
