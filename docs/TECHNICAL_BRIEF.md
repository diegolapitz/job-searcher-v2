# Job Searcher V2 - briefing tecnico

## 1. Objetivo del proyecto

Job Searcher V2 intenta resolver dos productos distintos sobre una misma base:

1. **Radar de oportunidades:** recolectar muchos avisos, eliminar repeticiones,
   evaluar su ajuste para una persona concreta y priorizar los que vale la pena
   revisar o aplicar.
2. **Inteligencia de mercado:** conservar observaciones históricas para analizar
   cómo cambian roles, skills, industrias, empresas, ubicaciones, modalidades y
   fuentes a lo largo del tiempo.

La estrategia activa es `v3.0-industrial-digital-agency`. El perfil es un
ingeniero químico con experiencia real en electrólisis de aluminio que combina
procesos, Oracle/SQL, Python, aplicaciones operativas, analytics e IA/ML. El
objetivo no es un puesto genérico de datos ni software: es transformar problemas
industriales reales con tecnología, aumentando impacto, autonomía, aprendizaje,
ingresos y opcionalidad. Oportunidades pesa 70% e inteligencia de mercado 30%.

## 2. Estado actual

- Repositorio: `https://github.com/diegolapitz/job-searcher-v2.git`.
- Rama: `main`.
- Stack: Python 3.12, FastAPI, SQLAlchemy, SQLite, React, Vite y Recharts.
- El código fuente sí está versionado. `.env`, SQLite, logs, dependencias y build
  del frontend están excluidos.
- La SQLite presente contiene 3.331 puestos y 4.122 snapshots recolectados el 12
  de noviembre de 2026. La corrida v3 agrego 282 canónicos sobre la base de
  3.049. No contiene el histórico operativo anterior.
- Último estado operativo conocido de la copia histórica, del 19 de junio de
  2026: 18.519 puestos canónicos. La corrida 7 recolectó 20.437 observaciones,
  creó 4.660 puestos y terminó `partial` por 15 errores en unos 92,7 minutos.
- La suite actual tiene 24 tests y pasa completa. Quedan warnings por
  `datetime.utcnow()`.

## 3. Arquitectura

```text
searches.yaml + sources.yaml + settings.yaml + strategy.yaml
                               |
                               v
                      app/pipeline.py
                               |
          +--------------------+--------------------+
          |                    |                    |
          v                    v                    v
    JobSpy/portales       ATS y feeds          APIs/verticales
          |                    |                    |
          +--------------------+--------------------+
                               |
                               v
                 normalizacion + identidad
                               |
                               v
                SQLite / SQLAlchemy ORM
                               |
                 +-------------+-------------+
                 |                           |
                 v                           v
          evaluacion AI/heuristica       FastAPI
                 |                           |
                 v                           v
             Telegram                  React dashboard
```

Módulos principales:

- `app/pipeline.py`: orquestación completa de una corrida.
- `app/connectors/`: adaptadores de las fuentes.
- `app/services/normalize.py`: normalización de payloads, país y modalidad.
- `app/services/identity.py`: identidad canónica y hashes de contenido.
- `app/services/evaluator.py`: scoring heurístico y evaluación Claude.
- `app/services/reevaluate.py`: backfill versionado de evaluaciones.
- `app/services/notifier.py`: envío transaccional a Telegram.
- `app/scheduler.py`: ejecución recurrente serial.
- `app/models.py`: modelo relacional.
- `app/api.py`: API local consumida por React.
- `frontend/src/App.jsx`: vistas y estado del dashboard.
- `app/cli.py`: comandos operativos.

## 4. Frecuencia real de ejecución

`config/settings.yaml` declara `interval_hours: 48`. El comando `schedule`
mantiene un proceso residente, ejecuta una corrida inmediatamente por defecto y
luego repite con ese intervalo. Las corridas son seriales dentro del proceso.

`run_v2.bat` solamente inicia:

- FastAPI en `127.0.0.1:8765`.
- Vite en `localhost:5173`.

La recolección manual sigue disponible:

```powershell
python -m app.cli run
```

Variantes disponibles:

```powershell
python -m app.cli run --dry-run
python -m app.cli run --no-notify
python -m app.cli run --sources greenhouse,ashby,hiringroom
python -m app.cli run --max-requests 50
python -m app.cli schedule
```

`run_scheduler.bat` inicia el scheduler. No instala una tarea de Windows ni se
reinicia solo después de apagar la PC; el proceso debe quedar abierto o ser
supervisado externamente.

`dry-run` igualmente recolecta y persiste datos, pero evita Claude, Telegram y
la shortlist. No es una simulación sin escrituras.

## 5. Plan de recolección actual

La matriz construida actualmente contiene **429 requests**. Las queries
temáticas se redujeron deliberadamente para evitar repeticiones por ciudad y
fuente sin perder familias, idiomas ni geografías:

| Fuente | Requests |
|---|---:|
| LinkedIn mediante JobSpy | 163 |
| Indeed mediante JobSpy | 163 |
| Computrabajo | 12 |
| Rigzone | 60 |
| Hiring Room | 15 |
| Greenhouse | 6 |
| Ashby | 3 |
| Lever | 3 |
| Remote OK | 1 |
| Jobicy | 1 |
| Arbeitnow | 1 |
| Remotive | 1 |

Adzuna agrega requests sólo si existen `ADZUNA_APP_ID` y `ADZUNA_APP_KEY`.
Google Jobs, Glassdoor y ZipRecruiter están soportados por JobSpy pero apagados.
Careermine, Bumeran y ZonaJobs están documentados como bloqueados.

Los ocho planes configurados son:

- Digitalización industrial.
- Analytics e IA industrial.
- Optimización y ML aplicado.
- Solutions y consultoría industrial.
- Control de procesos con componente digital.
- Project/business development como wildcard.
- Mercado europeo con relocation.
- Descubrimiento complementario en Computrabajo Argentina.
- Catálogos completos de 27 empresas en ATS/Hiring Room.
- Feeds remotos públicos.
- Vertical oil & gas de Rigzone.

Las queries usan ventanas de 72 a 168 horas. Los catálogos completos mantienen
8.760 horas y cada búsqueda convencional pide hasta 30 resultados. Los feeds y
ATS se leen una sola vez por fuente o board, no una vez por keyword.

## 6. Flujo de una corrida

1. Se crea una fila `Run` con estado `running`.
2. Se construye la matriz a partir de YAML y se eliminan requests idénticos.
3. Se procesa en lotes de 50 requests y 4 workers concurrentes para reducir
   rate limiting.
4. Cada conector devuelve `CollectionResult` con jobs, error y duración.
5. Los resultados de todas las requests quedan primero acumulados en memoria.
6. Después de terminar toda la red, se persisten:
   - métricas por request en `source_runs`;
   - payload crudo en `raw_jobs`;
   - puesto canónico en `jobs`;
   - observación histórica en `job_observations`.
7. Sólo los puestos canónicos nuevos se evalúan.
8. Todos reciben heurística; como máximo 30 candidatos por corrida live pasan a
   Claude, elegidos por pre-score y presencia de descripción.
9. Los que superan los thresholds de notificación de la estrategia activa y no
   son `discard` forman la shortlist.
10. Telegram recibe como máximo 12 avisos, aunque el umbral actual 90/75 es
    deliberadamente restrictivo.
11. La corrida termina como `success`, `partial` si hubo errores por fuente, o
    `failed` si escapó una excepción global.

## 7. Persistencia y modelo de datos

SQLite es la fuente de verdad local. Usa foreign keys, WAL y busy timeout de 5
segundos. No hay Alembic ni migraciones de esquema; sólo `create_all()`.

Tablas:

- `runs`: estado y totales de cada ejecución.
- `source_runs`: query, ubicación, resultados, nuevos, errores y duración por
  request.
- `raw_jobs`: snapshot completo del payload original.
- `jobs`: entidad canónica y datos normalizados.
- `job_observations`: cada reaparición de un puesto en una corrida/búsqueda.
- `evaluations`: versiones de scoring y extracción semántica.
- `applications`: estado manual del proceso de postulación.
- `notifications`: intentos y confirmación de alertas Telegram.

La migración V1 importa `jobs_master.csv`, crea snapshots y transforma el score
legacy en dimensiones aproximadas. El CSV ya no es almacenamiento primario.

## 8. Identidad, deduplicación y cambios

La identidad canónica prioriza:

1. `source + source_job_id`.
2. `source + URL normalizada`.
3. `source + hash(título, empresa, ubicación)`.

Esto deduplica bien dentro de una fuente, pero no une físicamente el mismo aviso
publicado en LinkedIn, Indeed y el ATS porque `source` forma parte de la
identidad. La API oculta coincidencias exactas de título, empresa y ubicación
para que no ocupen dos lugares en el dashboard; las métricas históricas todavía
pueden contar ambas entidades.

Cada payload tiene un hash de título, empresa, ubicación, descripción, fecha y
salario. Si cambia, se actualiza `last_changed_at` y la observación queda marcada
con `changed=True`.

No existe detección de cierre o expiración. `is_active` nace en `true` y nunca se
actualiza, de modo que “puestos activos” significa en la práctica “todos los
puestos que alguna vez se recolectaron”.

## 9. Normalización

Se normalizan título, empresa, ubicación, descripción, fuente, IDs, URLs, fecha
y salario original. País y modalidad se infieren mediante reglas simples sobre
el texto de ubicación.

Limitaciones:

- `city` y `region` existen en el modelo pero no se completan.
- La modalidad sólo se marca remota si aparece `remote/remoto` en la ubicación;
  el booleano `is_remote` de varios feeds no se usa en `normalize_job`.
- Si hay ubicación y no dice remoto/híbrido, se marca `onsite`.
- `salary_usd_year_min/max` existen pero nunca se calculan.
- La taxonomía geográfica es manual e incompleta.
- Varias ubicaciones ambiguas quedan sin país o mal clasificadas.

## 10. Evaluación y scoring

La evaluación separa:

- ajuste al perfil;
- ajuste técnico;
- ajuste industrial;
- valor de carrera;
- factibilidad de aplicación;
- seniority;
- confianza;
- skills, experiencia, inglés, industria, familia funcional, visa y relocation.

Prioridad:

```text
fit = profile*0.28 + technical*0.16 + industry*0.18
    + career*0.14 + seniority*0.08

priority = (fit*0.68 + feasibility*0.32) * max(confidence, 40)/100
```

La fórmula anterior queda sólo como referencia histórica. La v3 activa usa:

```text
fit = profile*0.25 + technical*0.20 + industry*0.15
    + career*0.30 + seniority*0.10

raw_priority = fit*0.70 + feasibility*0.30
priority = raw_priority * (1 - 0.25 * (1 - max(confidence, 55)/100))
```

El prompt de Claude se compone desde `config/strategy.yaml`. El mismo archivo
controla persona objetivo, reglas de factibilidad, heurística, pesos y
thresholds. `searches.yaml` sigue siendo independiente: cambiar la estrategia no
genera ni modifica queries automáticamente.

La heurística v3 separa señales industriales fuertes de contexto operativo,
detecta familias core/adjacent/exploratory por título y aplica exclusiones
contextuales. Argentina vale 100; remoto global/LATAM explícito 95; remoto de
alcance desconocido 35; exterior presencial sin apoyo 10; restricciones legales
explícitas 0; relocation o sponsorship explícito 75. La confianza incompleta
penaliza, pero ya no destruye el score multiplicándolo de forma directa.

La corrida normal evalúa sólo puestos nuevos. El comando `re-evaluate` selecciona
puestos cuya evaluación más reciente no corresponde a la versión activa y crea
una evaluación nueva sin borrar la anterior. Puede limitar volumen, simular el
conteo y usar Claude selectivamente. Una descripción enriquecida posteriormente
todavía no dispara reevaluación automática si la versión no cambió.

Si Claude falla durante una evaluación, se usa silenciosamente la heurística.
El método queda registrado, pero no hay alerta operacional sobre degradación del
servicio AI.

## 11. Notificaciones

Telegram se configura con `TELEGRAM_TOKEN` y `TELEGRAM_CHAT_ID`. Una notificación
se registra como `sent` sólo si la API confirma el envío. Si no está configurado,
la corrida continúa y guarda el error. El mensaje incluye título, empresa,
prioridad, factibilidad y enlace.

## 12. API

FastAPI expone:

- salud y última corrida;
- estrategia activa y thresholds;
- overview del dataset;
- listado y detalle de puestos;
- filtros por texto, scope, país, modalidad, fuente, estado, score y factibilidad;
- actualización del estado de postulación;
- tendencia mensual de nuevos canónicos;
- ranking de skills de la evaluación más reciente;
- historial de corridas;
- rendimiento acumulado por fuente.

La API escucha sólo en `127.0.0.1`, sin autenticación. Es apropiada para uso
local, no para exposición directa a Internet.

## 13. Dashboard

React presenta cinco vistas:

- **Hoy:** score mínimo 72, factibilidad mínima 60 y máximo 12 resultados.
- **Explorar:** sin umbrales de score/factibilidad.
- **Mercado:** volumen mensual, Argentina/remoto y ranking de skills.
- **Aplicaciones:** columnas saved/applied/interview/rejected.
- **Sistema:** corridas y métricas acumuladas por fuente.

Filtros rápidos: Argentina, remoto desde Argentina, remoto global, EE.UU.,
Europa y LATAM. También permite cruzar país, modalidad, fuente y score.

Limitaciones del frontend:

- Máximo 150 puestos, sin paginación ni infinite scroll.
- “Aplicaciones” filtra en cliente sólo los jobs ya cargados con los filtros
  vigentes; no consulta todas las aplicaciones.
- No refresca automáticamente durante una corrida.
- La estrategia activa se muestra, pero todavía no se puede editar desde UI.
- La vista de mercado mide `first_seen_at`; no ajusta por cobertura o cambios en
  cantidad de fuentes/queries.
- El texto “skills de AI” incluye también evaluaciones heurísticas.

## 14. Configuración declarada pero no implementada

Estos parámetros existen en YAML pero hoy no tienen efecto:

- `collection.request_timeout_seconds`.
- `collection.persist_batch_size`.
- `collection.evaluate_batch_size`.
- `source_health.disable_after_consecutive_failures`.
- `source_health.minimum_description_rate`.

Los conectores usan timeouts hardcodeados y ninguna fuente se deshabilita de
forma automática por mala salud.

## 15. Riesgos técnicos principales

1. **Versionado parcial:** evaluación y thresholds comparten estrategia, pero las
   queries siguen en otro YAML y no hay snapshot atómico de ambos contratos.
2. **Sin entidad relacional de estrategia:** `Evaluation.prompt_version` y
   `Run.notes` guardan la versión, pero no existe `strategy_id` ni snapshot del
   YAML para reproducir exactamente una corrida vieja.
3. **Reevaluación no reactiva:** existe backfill manual por versión, pero un
   cambio de descripción no dispara scoring nuevo automáticamente.
4. **Series de mercado no comparables:** cambios de fuentes, queries y lookback
   alteran el volumen sin quedar modelados como cobertura.
5. **Persistencia tardía:** se acumulan todas las respuestas en memoria y se
   escriben al terminar la recolección completa. Un corte puede perder progreso.
6. **Timeout global insuficiente:** JobSpy no está envuelto en un timeout externo;
   una request lenta puede retener un batch completo.
7. **Deduplicación física sólo por fuente:** la API oculta duplicados exactos,
   pero SQLite y las métricas todavía conservan entidades cross-source.
8. **Sin lifecycle:** no se identifican ofertas cerradas ni se actualiza
   `is_active`.
9. **Lifecycle incompleto:** existe detección de cambios, pero no de cierre.
10. **Sin migraciones de esquema ni backup automatizado.**
11. **Métricas de fuente acumuladas:** no distinguen salud reciente, cambios de
    configuración ni rendimiento marginal de cada búsqueda.
12. **Documentación parcialmente atrasada:** el roadmap todavía lista como
    futuros conectores que ya existen.

## 16. Tests actuales

Hay 23 tests sobre:

- conectores ATS;
- consistencia de la matriz de fuentes;
- fórmula y fallback del evaluador;
- scopes de filtros;
- identidad canónica;
- normalización;
- contrato de estrategia;
- reevaluación idempotente;
- ciclo acotado del scheduler.

No hay tests end-to-end de una corrida completa, de API con base real, de
Telegram, de recuperación ante interrupciones, de frontend ni de calidad del
dataset.

## 17. Qué debería resolver la siguiente iteración

La v3 ya activó el contrato de decisión y la matriz coherente. La siguiente
iteración debería persistir una entidad versionada `SearchStrategy` que agrupe:

- perfil objetivo y exclusiones;
- familias de roles y sinónimos;
- países, modalidades, visas y relocation;
- industrias y empresas;
- fuentes y cobertura;
- pesos, thresholds y prompt de evaluación;
- fecha de vigencia y versión.

Cada `Run`, `CollectionRequest` y `Evaluation` debería referenciar esa versión.
Así sería posible cambiar criterios, re-scorear el histórico y comparar períodos
sin mezclar metodologías.

Separar tres etapas explícitas:

1. **Ingesta amplia y durable:** persistencia por batch/request, retry, timeout,
   checkpoints y métricas de cobertura.
2. **Enriquecimiento versionado:** normalización geográfica, deduplicación
   cross-source, lifecycle, skills y salarios.
3. **Decisión personal:** evaluación barata inicial, evaluación LLM selectiva,
   feedback manual y calibración contra aplicaciones reales.

Para inteligencia de mercado se necesita además:

- snapshots de cobertura por corrida;
- métricas por query/fuente, no sólo por fuente;
- cohortes comparables;
- roles/skills con taxonomías estables;
- distinción entre fecha publicada, primera observación y última observación;
- detección de cierres y duración de avisos;
- separación entre demanda observada y sesgo del recolector.

## 18. Incertidumbres que todavía requieren feedback

1. Compensación actual y mejora mínima para justificar un cambio.
2. Ciudadanía o permisos laborales adicionales.
3. Nivel de inglés operativo real.
4. Máximo sostenible de presencialidad y commute en Buenos Aires.
5. Feedback explícito sobre falsos positivos, descartes y aplicaciones.
6. Presupuesto aceptable para scraping pago y LLM.

## 19. Resumen para otro LLM

El sistema es un recolector local extensible con dos salidas explícitas: radar
personal e inteligencia de mercado. La estrategia v3, las 429 requests, el
scoring, la geografía, el dashboard y las alertas comparten criterios activos.
El histórico completo fue recalculado sin Claude y la vista Hoy quedó reducida a
tres oportunidades únicas sobre 3.331 puestos, con tope de 12. Siguen faltando lifecycle,
persistencia incremental, deduplicación física cross-source, snapshots de
cobertura y series comparables. La calidad futura depende sobre todo de feedback
manual y de medir yield marginal por query/fuente.
