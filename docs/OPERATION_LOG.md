# Registro operativo

## 2026-11-12

### Run 1 - ingesta pública

- Fuentes: Remote OK, Jobicy, Arbeitnow y Remotive.
- Requests: 4.
- Capturas: 2.735.
- Puestos canónicos nuevos: 2.732.
- Evaluaciones heurísticas: 2.732.
- Errores: 0.
- Duración: 33,5 segundos.
- Notificaciones: desactivadas para no alertar con el perfil heredado.

### Run 2 - recalibración de visibilidad

- Estrategia: `legacy-bootstrap-2026-11-r2`.
- Puestos reevaluados: 2.732.
- Motivo: el umbral 55 ocultaba todos los resultados heurísticos.

### Run 3 - factibilidad remota

- Estrategia: `legacy-bootstrap-2026-11-r3`.
- Puestos reevaluados: 2.732.
- Motivo: distinguir remoto global/LATAM, alcance desconocido y remoto
  restringido geográficamente.
- Resultado operativo: seis puestos pasan la vista Hoy bajo 35/40.

### Run 4 - ingeniería en Argentina

- Fuentes: LinkedIn e Indeed.
- Requests: 60 búsquedas núcleo en Argentina y ciudades principales.
- Capturas: 562.
- Puestos canónicos nuevos: 275.
- Errores de corrida: 0.
- Duración: 296,8 segundos.
- Observación: LinkedIn aplicó HTTP 429 durante algunos reintentos; el lote
  completó, pero confirma que no conviene disparar las 786 queries seguidas.

### Run 5 - Computrabajo

- Requests: 30.
- Capturas: 252.
- Puestos canónicos nuevos: 42.
- Errores de corrida: 0.
- Duración: 48,1 segundos.
- Calidad: los 42 puestos quedaron sin descripción; su evaluación heurística se
  apoya casi exclusivamente en título y ubicación.

### Estado posterior

- Puestos canónicos: 3.049.
- Argentina: 268.
- Visibles en Hoy bajo estrategia heredada 35/40: 127.
- Duplicados de identidad canónica: 0.
- Descripciones faltantes: 42.

La evidencia detallada permanece en SQLite (`runs`, `source_runs`,
`evaluations`) y en `logs/job-searcher-v2.jsonl`; ambos están excluidos de Git
porque contienen estado local y pueden crecer significativamente.

### Activacion de estrategia v3

- Estrategia: `v3.0-industrial-digital-agency` (`status: active`).
- Fuente completa recibida y preservada localmente fuera de Git.
- Backup previo: `data/backups/job_searcher_v2-before-v3-20261112-200548.sqlite3`.
- Matriz nueva: 429 requests totales.
- Queries tematicas: 163 LinkedIn, 163 Indeed y 12 Computrabajo.
- Cobertura complementaria: 60 Rigzone, 27 ATS/Hiring Room y cuatro feeds.
- Concurrencia reducida de 8 a 4 workers y lotes de 100 a 50 para limitar 429.

### Runs 6 a 10 - recalibracion completa

- Las primeras pasadas preservaron 3.049 evaluaciones heuristicas nuevas y la
  final 3.329; no se llamo a Claude porque no existe `ANTHROPIC_API_KEY` activa.
- Run 6 activo la formula y factibilidad v3.
- Run 7 corrigio falsos positivos por keywords genericas y coincidencias parciales.
- Run 8 penalizo data/software sin contexto industrial y excluyo talent pools.
- Run 9 ejecuto 40 queries v3: 513 capturas, 280 canónicos nuevos y tres errores
  de validacion de pais provocados por `Remote LATAM`.
- Run 10 recalibro los 3.329 avisos con una condicion explicita de dominio:
  industria fuerte y titulo objetivo o una interseccion tecnica robusta.
- Resultado final: 3 vacantes unicas pasan 72/60 tras deduplicar variantes entre
  fuentes. Alta prioridad 82/75: 1. Notificacion 90/75: 0.
- Los resultados visibles son Grupo Corven, Mercado Envios y Rio Tinto.
- Hallazgo: los IDs canonicos siguen siendo por fuente; la API deduplica la vista,
  pero las metricas historicas todavia pueden contar duplicados cross-source.

### Run 11 - validacion de remoto Argentina

- Se reemplazo `Remote LATAM` por `Remote, Argentina` para evitar paises no
  soportados por el validador interno de JobSpy.
- Dos queries LinkedIn: 60 capturas, 2 canónicos nuevos, 0 errores, 42,9 segundos.
- Estado local: 3.331 jobs, 4.122 snapshots, 21.271 evaluaciones y 362 jobs con
  pais Argentina.
- API reiniciada en `127.0.0.1:8765`; Vite activo en `127.0.0.1:5173`.
- Scheduler residente iniciado con `--no-run-now`; proximo ciclo en 48 horas.
- QA visual: estrategia, tres filas unicas, filtros cruzados y detalle correctos;
  consola sin warnings/errores y tabla sin overflow horizontal.
