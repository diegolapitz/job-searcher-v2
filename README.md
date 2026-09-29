# Job Searcher V2

Aplicación local para buscar oportunidades laborales y estudiar cómo evoluciona el mercado de trabajo. Reúne avisos de distintas fuentes, conserva sus observaciones en el tiempo, normaliza duplicados y ayuda a priorizar postulaciones. El mismo historial alimenta un tablero con tendencias de roles, habilidades, empresas y ubicaciones.

## Finalidad

El proyecto nació para combinar dos necesidades: encontrar vacantes relevantes para un perfil de ingeniería y análisis de datos, y construir una base histórica que permita entender qué pide el mercado. Las búsquedas, empresas objetivo y criterios de evaluación se pueden adaptar en `config/`.

## Cómo está construido

- **Python 3.12** coordina la recolección, normalización, deduplicación y evaluación de avisos. Los conectores consultan bolsas de trabajo, feeds públicos y sistemas de contratación de empresas.
- **SQLite + SQLAlchemy** guardan avisos, capturas originales, evaluaciones y corridas. Los archivos locales de datos se excluyen del repositorio.
- **FastAPI** expone los datos y operaciones al tablero, además de documentación en `/docs`.
- **React + Vite** presentan el radar de oportunidades y las vistas de inteligencia de mercado.
- La evaluación usa reglas locales y, opcionalmente, **Claude** para los candidatos que superan el filtro previo. Las alertas por **Telegram** también son opcionales.

## Puesta en marcha

Requisitos: Python 3.12 y Node.js con npm. En Windows, `setup_v2.bat` instala las dependencias e inicializa una base vacía; `run_v2.bat` abre la API y el tablero. También se puede iniciar manualmente:

```powershell
python -m pip install -e ".[dev]"
python -m app.cli init-db
python -m app.cli serve
```

En otra terminal:

```powershell
cd frontend
npm install
npm run dev
```

Tablero: http://localhost:5173 · API: http://localhost:8765 · Documentación API: http://localhost:8765/docs

Copiá `.env.example` a `.env` solo si vas a usar integraciones que requieren claves. Sin claves, podés explorar el tablero con una base vacía y ejecutar recolecciones compatibles con fuentes públicas. Para probar una corrida sin evaluación de IA ni notificaciones:

```powershell
python -m app.cli run --dry-run --max-requests 50
```

`run --dry-run` sí consulta fuentes externas y puede tardar. La ejecución normal (`python -m app.cli run`) puede usar servicios con costo y enviar avisos si configuraste sus credenciales. Ajustá `config/settings.yaml` y `config/sources.yaml` antes de activarla.

Si tenés un CSV generado por la versión anterior, lo podés importar con `python -m app.cli migrate-v1 RUTA_AL_CSV`. El CSV histórico y la base local no forman parte de este repositorio.

## Organización

| Carpeta | Contenido |
| --- | --- |
| `app/connectors/` | Integraciones con fuentes de avisos |
| `app/services/` | Identidad, normalización, evaluación y alertas |
| `app/api.py`, `app/cli.py`, `app/pipeline.py` | API, comandos y coordinación de corridas |
| `config/` | Búsquedas, empresas y parámetros |
| `frontend/` | Tablero React |
| `tests/` | Pruebas del núcleo |

La cobertura y disponibilidad de cada fuente pueden cambiar con el tiempo. El sistema conserva las observaciones originales para poder auditar resultados y evita interpretar cambios de cobertura como cambios del mercado.
