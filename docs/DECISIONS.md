# Decisiones de arquitectura

## 2026-06-12 — Crear V2 aislada

La carpeta padre queda como V1 operativa e histórica. Toda modificación nueva
vive en `job-searcher-v2/`.

## SQLite como fuente de verdad

Se eligió SQLite porque:

- El sistema es local y de un solo usuario.
- Permite transacciones, índices, relaciones y auditoría.
- No introduce infraestructura remota.
- Puede migrarse posteriormente a PostgreSQL mediante SQLAlchemy.

El CSV pasa a ser formato de importación/exportación, no almacenamiento primario.

## FastAPI + React

FastAPI expone datos y operaciones. React renderiza el producto. Esta separación
evita que scraping, persistencia y HTML vuelvan a vivir en un solo archivo.

## Identidad canónica

Orden de preferencia:

1. ID de la plataforma.
2. URL normalizada.
3. Hash de título, empresa y ubicación normalizados.

Los nulos se normalizan antes de comparar.

## Capturas crudas

Nunca se descarta silenciosamente un resultado. `raw_jobs` conserva el payload y
`job_observations` registra cada reaparición. La shortlist es una vista derivada.
Una captura cruda puede repetirse sin cambios: esa repetición registra que el
puesto seguía visible. La unicidad se aplica al puesto canónico, no al snapshot.

## Scoring multidimensional

El score anterior mezclaba afinidad y factibilidad. V2 separa:

- Ajuste al perfil.
- Ajuste técnico.
- Ajuste industrial.
- Valor de carrera.
- Factibilidad de aplicación.
- Seniority.
- Confianza.

La prioridad final no puede ocultar una factibilidad baja.

## Fuentes

Climatebase se excluyó porque la API falló en la auditoría del 12 de junio de
2026. Remotive permanece, pero su rendimiento queda medido. No se agrega un
conector sin métricas de resultados, descripciones, errores y nuevos canónicos.

## Alertas

Una alerta se considera enviada únicamente después de que Telegram confirma el
request. Un reinicio no convierte automáticamente una oportunidad en notificada.
