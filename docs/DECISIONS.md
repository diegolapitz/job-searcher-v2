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

## 2026-11-12 — Estrategia versionada y operación recurrente

Perfil, heurística, pesos, factibilidad y thresholds pasan a
`config/strategy.yaml`. La versión de estrategia queda registrada en cada nueva
corrida y evaluación. Se agrega un backfill que genera evaluaciones nuevas sin
sobrescribir las anteriores y un scheduler residente, serial, que evita solapar
corridas dentro del mismo proceso.

Esta es una capa de compatibilidad previa a modelar `SearchStrategy` como entidad
relacional. Las búsquedas continúan en `searches.yaml`, y la versión de cada
corrida queda por ahora en `Run.notes`.

## 2026-11-12 — Activar estrategia industrial-digital v3

Se adopta `v3.0-industrial-digital-agency` como contrato operativo. Valor de
carrera pasa a ser la dimension de fit con mayor peso. Factibilidad permanece
separada y exige evidencia para remoto internacional, sponsorship o relocation.
Healthcare y data/software genericos dejan de ser objetivos.

La especificacion original se preserva localmente y esta ignorada por Git por
contener contexto personal; `config/strategy.yaml` es su traduccion ejecutable.
La matriz se limita a 429 requests de alta senal. La amplitud se logra con
keywords y fuentes complementarias, no repitiendo feeds completos por cada
termino. El dashboard muestra como maximo 12 oportunidades bajo 72/60.

La identidad persistida sigue siendo source-scoped para no fusionar avisos de
forma destructiva. Como mitigacion inmediata, la API oculta duplicados exactos
de titulo, empresa y ubicacion. La unificacion historica queda pendiente.
