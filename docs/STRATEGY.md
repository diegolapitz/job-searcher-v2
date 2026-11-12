# Estrategia de búsqueda y evaluación

`config/strategy.yaml` es el contrato operativo para decidir qué constituye una
buena oportunidad. Define perfil, familias objetivo y excluidas, keywords del
fallback, factibilidad geográfica, pesos y thresholds.

La version activa es `v3.0-industrial-digital-agency`. Prioriza digitalizacion,
analytics/IA industrial, optimizacion, solutions y control avanzado; conserva
product, data engineering, consulting y project development como familias
adyacentes o exploratorias. Los defaults operativos son 72/60 para Hoy, 82/75
para alta prioridad, 90/75 para Telegram y 12 revisiones diarias.

La especificacion completa recibida se conserva localmente en
`docs/strategy-v3-source.yaml`. Ese archivo contiene contexto personal, esta
ignorado por Git y no lo consume el runtime. La traduccion publica y ejecutable
vive en `config/strategy.yaml`; la matriz correspondiente esta en
`config/searches.yaml`.

## Cambio de criterios

1. Reemplazar el perfil y las listas de términos.
2. Ajustar factibilidad, pesos y thresholds.
3. Asignar una `version` nueva y marcar `status: active`.
4. Actualizar `config/searches.yaml` si cambiaron roles, ubicaciones o amplitud
   de ingesta. La estrategia no genera queries automáticamente.
5. Reiniciar API y scheduler para limpiar la caché de configuración.
6. Medir el impacto antes de escribir:

```powershell
py -3.12 -m app.cli re-evaluate --dry-run
```

7. Persistir evaluaciones nuevas:

```powershell
py -3.12 -m app.cli re-evaluate
```

Agregar `--use-ai` para enviar a Claude, como máximo, los mejores candidatos
definidos por `ai.max_evaluations_per_run`. Las evaluaciones anteriores se
conservan para auditoría y la API consume siempre la más reciente.

## Umbrales

- `ai_prefilter_priority`: candidatos que pueden pasar a Claude.
- `today_priority` y `today_feasibility`: vista inicial del dashboard.
- `high_priority` y `high_feasibility`: KPI de alta prioridad.
- `notification_priority` y `notification_feasibility`: shortlist de Telegram.

Cambiar un threshold no reescribe scores. Cambiar pesos, perfil o heurística sí
requiere una versión nueva y `re-evaluate`.
