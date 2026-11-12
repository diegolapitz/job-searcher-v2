# Changelog

## 2026-11-12 - Estrategia v3 industrial-digital

- Se activo `v3.0-industrial-digital-agency`; la especificacion personal fuente
  se preserva localmente y queda excluida del repositorio publico.
- Se reemplazo la matriz heredada de 1.899 requests por 429 requests de mayor
  senal, con ocho planes de busqueda y cobertura ATS/feed sin repeticion.
- Se implemento scoring contextual por familia, industria fuerte, tecnologia,
  valor de carrera, seniority, confianza y factibilidad geografica.
- Se agregaron exclusiones contextuales para BI/data/software genericos,
  funciones corporativas, proceso tradicional y talent pools.
- La vista Hoy usa 72/60 y limita la revision diaria a 12 resultados.
- `Remoto desde AR` usa factibilidad de la evaluacion vigente, no un search ID.
- Las observaciones ahora registran cambios reales y los jobs guardan provenance
  de familia, search ID y version de estrategia.
- La API oculta duplicados cross-source con titulo, ciudad y empresa equivalentes.
- Se ajusto el layout del listado para evitar scroll horizontal junto al detalle.
- Se recalcularon 3.331 puestos locales y se conservaron las evaluaciones
  anteriores. La vista final contiene tres vacantes unicas.

## 2026-11-12

### Agregado

- Estrategia versionada en `config/strategy.yaml` para perfil, heurística,
  factibilidad, scoring y thresholds.
- Endpoint `GET /api/strategy` e indicador de estrategia activa en el dashboard.
- Comando `re-evaluate` para recalcular el histórico preservando evaluaciones
  anteriores y evitando repetir trabajos ya evaluados con la versión vigente.
- Comando `schedule` y `run_scheduler.bat` para ejecutar corridas recurrentes.
- Pruebas aisladas para versionado, backfill y scheduler.
- Briefing técnico actualizado en `docs/TECHNICAL_BRIEF.md`.

### Cambiado

- Claude, fallback heurístico, pipeline, API y dashboard comparten una única
  fuente de thresholds.
- La vista Hoy usa 35/40 mientras opera sólo con heurística; con el umbral
  heredado 55/40 ninguna de las 2.732 primeras vacantes públicas era visible.
- El fallback diferencia remoto global/LATAM, remoto de alcance desconocido y
  remoto explícitamente restringido; ya no presume que todo remoto es aplicable.
- La versión de estrategia se registra en evaluaciones y notas de corrida.
- Claude queda desactivado automáticamente si falta `ANTHROPIC_API_KEY`, sin
  impedir el scoring heurístico.

### Estado pendiente en bootstrap (resuelto por v3)

- `legacy-bootstrap-2026-11-r3` conserva temporalmente el perfil anterior y está
  marcado `needs_review` hasta cargar los nuevos criterios de búsqueda.
- La base SQLite local contiene la corrida pública nueva, pero el histórico de
  la instalación previa no está incluido en esta copia ni en Git.

### Verificación operativa

- Corrida real sobre Remote OK, Jobicy, Arbeitnow y Remotive: 2.735 capturas,
  2.732 puestos canónicos nuevos, cero errores y 33,5 segundos.
- Reevaluación completa con estrategia `legacy-bootstrap-2026-11-r3`: 2.732
  puestos, sin llamadas a Claude.
- Lotes locales posteriores: 562 capturas de LinkedIn/Indeed (275 puestos
  nuevos) y 252 de Computrabajo (42 nuevos), ambos sin errores de corrida.
- Estado final local: 3.049 puestos, 268 de Argentina y 127 visibles en Hoy.
- Dashboard validado con cruce de filtros `Remoto + remoteok` sin errores de
  consola.
