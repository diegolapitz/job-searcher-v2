import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Globe2, MapPin, Plane, RotateCcw, Wifi } from "lucide-react";
import { api } from "./api";
import {
  JobDetail,
  JobTable,
  Metric,
  Sidebar,
  Topbar,
  metricIcons,
} from "./components";

const emptyOverview = {
  total_jobs: 0,
  active_jobs: 0,
  high_priority: 0,
  argentina_jobs: 0,
  new_last_30_days: 0,
};

const emptyFilterOptions = { scopes: [], countries: [], work_modes: [] };

export default function App() {
  const [view, setView] = useState("today");
  const [query, setQuery] = useState("");
  const [overview, setOverview] = useState(emptyOverview);
  const [jobs, setJobs] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);
  const [trends, setTrends] = useState([]);
  const [skills, setSkills] = useState([]);
  const [runs, setRuns] = useState([]);
  const [sources, setSources] = useState([]);
  const [filterOptions, setFilterOptions] = useState(emptyFilterOptions);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState({
    scope: "",
    country: "",
    work_mode: "",
    source: "",
    minimum_priority: 55,
    minimum_feasibility: 40,
  });

  const loadJobs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.jobs({ ...filters, q: query, limit: 150 });
      setJobs(data);
      if (!data.some((job) => job.id === selectedId)) {
        setSelectedId(data[0]?.id ?? null);
        if (!data[0]) setSelectedJob(null);
      }
      setError("");
    } catch (requestError) {
      setError("No se pudo conectar con la API. Iniciá el backend en el puerto 8765.");
    } finally {
      setLoading(false);
    }
  }, [filters, query, selectedId]);

  useEffect(() => {
    Promise.all([
      api.overview(), api.trends(), api.skills(), api.runs(), api.sources(),
      api.filterOptions(),
    ])
      .then(([overviewData, trendData, skillData, runData, sourceData, filterData]) => {
        setOverview(overviewData);
        setTrends(trendData);
        setSkills(skillData);
        setRuns(runData);
        setSources(sourceData);
        setFilterOptions(filterData);
      })
      .catch(() => setError("El backend todavía no está disponible."));
  }, []);

  useEffect(() => {
    loadJobs();
  }, [filters]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (view === "explore") {
      setFilters((current) => ({
        ...current,
        minimum_priority: 0,
        minimum_feasibility: 0,
      }));
    } else if (view === "today") {
      setFilters((current) => ({
        ...current,
        minimum_priority: 55,
        minimum_feasibility: 40,
      }));
    }
  }, [view]);

  useEffect(() => {
    if (!selectedId) return;
    api.job(selectedId).then(setSelectedJob).catch(() => setSelectedJob(null));
  }, [selectedId]);

  const updateStatus = async (status) => {
    if (!selectedJob) return;
    await api.updateApplication(selectedJob.id, {
      status,
      notes: selectedJob.application?.notes || "",
    });
    setSelectedJob(await api.job(selectedJob.id));
    await loadJobs();
  };

  const title = useMemo(
    () =>
      ({
        today: ["Radar de oportunidades", "Prioridad real, no solo volumen recolectado."],
        explore: ["Explorar el mercado", "Buscá y compará el dataset completo."],
        market: ["Inteligencia de mercado", "Señales longitudinales con cobertura explícita."],
        applications: ["Pipeline de aplicaciones", "Seguimiento persistente de decisiones y avances."],
        system: ["Salud del sistema", "Fuentes, corridas, errores y rendimiento."],
      })[view],
    [view],
  );

  return (
    <div className="app-shell">
      <Sidebar view={view} setView={setView} />
      <main>
        <Topbar query={query} setQuery={setQuery} onSearch={loadJobs} />
        <div className="page">
          <div className="page-heading">
            <div><h1>{title[0]}</h1><p>{title[1]}</p></div>
            <span>Últimos datos locales</span>
          </div>
          {error && <div className="error-banner">{error}</div>}
          {(view === "today" || view === "explore") && (
            <OpportunityView
              overview={overview}
              jobs={jobs}
              loading={loading}
              selectedId={selectedId}
              selectedJob={selectedJob}
              setSelectedId={setSelectedId}
              filters={filters}
              filterOptions={filterOptions}
              setFilters={setFilters}
              loadJobs={loadJobs}
              updateStatus={updateStatus}
              explore={view === "explore"}
            />
          )}
          {view === "market" && <MarketView trends={trends} skills={skills} overview={overview} />}
          {view === "applications" && (
            <ApplicationsView jobs={jobs.filter((job) => job.application)} setSelectedId={setSelectedId} />
          )}
          {view === "system" && <SystemView runs={runs} sources={sources} />}
        </div>
      </main>
    </div>
  );
}

function OpportunityView(props) {
  const {
    overview, jobs, loading, selectedId, selectedJob, setSelectedId,
    filters, filterOptions, setFilters, loadJobs, updateStatus, explore,
  } = props;
  const setScope = (scope) => setFilters({
    ...filters,
    scope: filters.scope === scope ? "" : scope,
    country: "",
    work_mode: "",
  });
  const resetFilters = () => setFilters({
    scope: "",
    country: "",
    work_mode: "",
    source: "",
    minimum_priority: explore ? 0 : 55,
    minimum_feasibility: explore ? 0 : 40,
  });
  const activeFilters = [
    filters.scope && filterOptions.scopes.find((item) => item.value === filters.scope)?.label,
    filters.country,
    filters.work_mode && { remote: "Remoto", hybrid: "Híbrido", onsite: "Presencial" }[filters.work_mode],
    filters.source,
    filters.minimum_priority > 0 && `Score ≥ ${filters.minimum_priority}`,
    filters.minimum_feasibility > 0 && `Aplicabilidad ≥ ${filters.minimum_feasibility}`,
  ].filter(Boolean);
  return (
    <>
      <div className="metrics">
        <Metric label="Dataset" value={overview.total_jobs.toLocaleString()} detail={`${overview.active_jobs} activos`} icon={metricIcons.total} />
        <Metric label="Alta prioridad" value={overview.high_priority} detail="Ajuste + aplicabilidad" tone="positive" icon={metricIcons.priority} />
        <Metric label="Argentina" value={overview.argentina_jobs} detail="Cobertura local" icon={metricIcons.argentina} />
        <Metric label="Últimos 30 días" value={overview.new_last_30_days} detail="Nuevos canónicos" icon={metricIcons.recent} />
      </div>
      <section className="filter-bar">
        <div className="quick-scopes" aria-label="Alcances rápidos">
          <button
            className={!filters.scope && !filters.country && !filters.work_mode ? "scope-chip active" : "scope-chip"}
            onClick={() => setFilters({ ...filters, scope: "", country: "", work_mode: "" })}
          >
            <Globe2 size={14} /> Todo
          </button>
          {filterOptions.scopes.map((scope) => {
            const Icon = scope.value === "argentina"
              ? MapPin
              : scope.value.includes("remote") ? Wifi : scope.value === "usa" ? Plane : Globe2;
            return (
              <button
                key={scope.value}
                className={filters.scope === scope.value ? "scope-chip active" : "scope-chip"}
                onClick={() => setScope(scope.value)}
                title={scope.value === "argentina_remote" ? "Puestos encontrados por las búsquedas de trabajo remoto para LATAM" : undefined}
              >
                <Icon size={14} /> {scope.label}
                <span>{scope.count.toLocaleString()}</span>
              </button>
            );
          })}
        </div>
        <div className="advanced-filters">
          <label>
            <span>País</span>
            <select
              value={filters.country}
              onChange={(event) => setFilters({ ...filters, scope: "", country: event.target.value })}
            >
              <option value="">Cualquier país</option>
              {filterOptions.countries.map((country) => (
                <option key={country.value} value={country.value}>
                  {country.label} ({country.count.toLocaleString()})
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Modalidad</span>
            <select
              value={filters.work_mode}
              onChange={(event) => setFilters({ ...filters, scope: "", work_mode: event.target.value })}
            >
              <option value="">Cualquiera</option>
              <option value="remote">Remoto</option>
              <option value="hybrid">Híbrido</option>
              <option value="onsite">Presencial</option>
            </select>
          </label>
          <label>
            <span>Fuente</span>
            <select value={filters.source} onChange={(event) => setFilters({ ...filters, source: event.target.value })}>
              <option value="">Todas</option>
              {[
                "linkedin", "indeed", "computrabajo", "remotive", "hiringroom",
                "greenhouse", "ashby", "lever", "arbeitnow", "remoteok", "jobicy", "rigzone",
              ].map((source) => <option key={source} value={source}>{source}</option>)}
            </select>
          </label>
          <label>
            <span>Score mínimo</span>
            <select
              value={filters.minimum_priority}
              onChange={(event) => setFilters({ ...filters, minimum_priority: Number(event.target.value) })}
            >
              <option value="0">Todos</option>
              <option value="40">40+</option>
              <option value="55">55+</option>
              <option value="72">72+</option>
              <option value="80">80+</option>
            </select>
          </label>
          <button className="reset-filters" onClick={resetFilters} title="Limpiar filtros">
            <RotateCcw size={15} />
          </button>
        </div>
        <div className="filter-summary">
          <span>{activeFilters.length ? activeFilters.join(" · ") : "Sin filtros: viendo todo el mercado"}</span>
          <strong>{jobs.length} mostrados</strong>
        </div>
      </section>
      <div className="workspace">
        <section className="opportunity-list">
          <div className="section-head">
            <div><h2>{explore ? "Dataset completo" : "Oportunidades priorizadas"}</h2><span>{jobs.length} resultados visibles</span></div>
            <button className="refresh-button" onClick={loadJobs}>Actualizar</button>
          </div>
          <JobTable jobs={jobs} selectedId={selectedId} onSelect={setSelectedId} loading={loading} />
        </section>
        <JobDetail job={selectedJob} onStatus={updateStatus} />
      </div>
    </>
  );
}

function MarketView({ trends, skills, overview }) {
  const maxSkill = Math.max(...skills.map((item) => item.count), 1);
  return (
    <div className="market-grid">
      <section className="chart-panel wide">
        <div className="section-head">
          <div><h2>Volumen observado</h2><span>Separá crecimiento del mercado de cambios de cobertura.</span></div>
        </div>
        <div className="chart">
          <ResponsiveContainer width="100%" height={310}>
            <AreaChart data={trends}>
              <defs>
                <linearGradient id="areaJobs" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#4d8cff" stopOpacity={0.28} />
                  <stop offset="100%" stopColor="#4d8cff" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#202632" vertical={false} />
              <XAxis dataKey="period" stroke="#667085" tickLine={false} axisLine={false} />
              <YAxis stroke="#667085" tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "#111722", border: "1px solid #2a3240" }} />
              <Area type="monotone" dataKey="jobs" stroke="#4d8cff" fill="url(#areaJobs)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </section>
      <section className="chart-panel">
        <div className="section-head"><div><h2>Skills demandadas</h2><span>Evaluación AI más reciente por puesto.</span></div></div>
        <div className="skill-ranking">
          {skills.slice(0, 12).map((item, index) => (
            <div key={item.skill}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <b>{item.skill}</b>
              <i><em style={{ width: `${(item.count / maxSkill) * 100}%` }} /></i>
              <strong>{item.count}</strong>
            </div>
          ))}
        </div>
      </section>
      <section className="chart-panel">
        <div className="section-head"><div><h2>Cobertura actual</h2><span>Contexto para interpretar tendencias.</span></div></div>
        <div className="coverage-list">
          <p><span>Total canónico</span><strong>{overview.total_jobs}</strong></p>
          <p><span>Argentina</span><strong>{overview.argentina_jobs}</strong></p>
          <p><span>Alta prioridad</span><strong>{overview.high_priority}</strong></p>
          <p><span>Nuevos 30 días</span><strong>{overview.new_last_30_days}</strong></p>
        </div>
      </section>
    </div>
  );
}

function ApplicationsView({ jobs, setSelectedId }) {
  return (
    <section className="pipeline-panel">
      {["saved", "applied", "interview", "rejected"].map((status) => (
        <div className="pipeline-column" key={status}>
          <h2>{status}</h2>
          {jobs.filter((job) => job.application?.status === status).map((job) => (
            <button key={job.id} onClick={() => setSelectedId(job.id)}>
              <b>{job.title}</b><span>{job.company}</span><small>{job.location}</small>
            </button>
          ))}
        </div>
      ))}
    </section>
  );
}

function SystemView({ runs, sources }) {
  return (
    <div className="system-grid">
      <section className="chart-panel">
        <div className="section-head"><div><h2>Rendimiento por fuente</h2><span>Yield y fallas acumuladas.</span></div></div>
        <div className="system-table">
          <div><b>Fuente</b><b>Requests</b><b>Resultados</b><b>Nuevos</b><b>Fallas</b></div>
          {sources.map((source) => (
            <div key={source.source}>
              <strong>{source.source}</strong><span>{source.requests}</span><span>{source.results}</span>
              <span>{source.new_jobs}</span><span>{source.failures}</span>
            </div>
          ))}
        </div>
      </section>
      <section className="chart-panel">
        <div className="section-head"><div><h2>Últimas corridas</h2><span>Estado operativo y volumen.</span></div></div>
        <div className="run-list">
          {runs.map((run) => (
            <div key={run.id}>
              <i className={`run-${run.status}`} />
              <span><b>Run #{run.id}</b><small>{new Date(run.started_at).toLocaleString()}</small></span>
              <strong>{run.new_count} nuevos</strong>
              <em>{run.status}</em>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
