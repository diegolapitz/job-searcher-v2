# Job Searcher

Armé este proyecto para seguir búsquedas de empleo en ingeniería y análisis de datos sin tener que revisar cada portal por separado. Junta ofertas de distintas fuentes, detecta duplicados y permite ordenar las oportunidades según su relevancia.

Además de mostrar vacantes, guarda un historial para ver qué roles, habilidades y empresas aparecen con más frecuencia.

## Qué hace

- Recolecta y normaliza ofertas de portales, feeds públicos y páginas de empleo de empresas.
- Guarda las ofertas y sus cambios en una base local.
- Muestra un tablero para filtrar oportunidades, revisar postulaciones y explorar tendencias del mercado.
- Puede evaluar ofertas con Claude y enviar alertas por Telegram si se configuran esas integraciones.
- Usa una estrategia versionada para que scoring, umbrales, dashboard y alertas compartan el mismo criterio.

## Tecnologías

Backend en **Python** con **FastAPI**, **SQLAlchemy** y **SQLite**. Frontend en **React** con **Vite**. Las búsquedas y fuentes se ajustan desde los archivos de `config/`.

La estrategia activa, `v3.0-industrial-digital-agency`, busca perfiles hibridos
de ingenieria industrial/procesos con digitalizacion, analytics, IA, software y
optimizacion aplicada. La vista Hoy exige score 72, factibilidad 60 y muestra
como maximo 12 oportunidades. La matriz actual ejecuta 429 requests entre
LinkedIn, Indeed, Computrabajo, ATS, feeds remotos y Rigzone.

## Uso local

Con Python 3.12 y Node.js instalados, en Windows ejecutá `setup_v2.bat` una vez y después `run_v2.bat`. El tablero queda en [localhost:5173](http://localhost:5173).

Las claves para Claude, Telegram y otras fuentes son opcionales y se configuran en `.env` a partir de `.env.example`. La base de datos local y las credenciales no están incluidas en el repositorio.

## Operación

Una corrida manual:

```powershell
py -3.12 -m app.cli run --no-notify
```

El scheduler residente usa `interval_hours` de `config/settings.yaml` (48 horas por defecto):

```powershell
run_scheduler.bat
```

La estrategia de perfil, scoring y umbrales vive en `config/strategy.yaml`. Después de cambiar su `version`, se puede recalcular el histórico sin volver a scrapear:

```powershell
py -3.12 -m app.cli re-evaluate --dry-run
py -3.12 -m app.cli re-evaluate --use-ai
```

El segundo comando usa Claude sólo si `ANTHROPIC_API_KEY` está configurada; el resto se evalúa con la heurística versionada.
