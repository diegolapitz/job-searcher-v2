import {
  Activity,
  BarChart3,
  BriefcaseBusiness,
  Building2,
  Check,
  ChevronRight,
  CircleDot,
  Database,
  ExternalLink,
  FileSearch,
  Gauge,
  HeartPulse,
  MapPin,
  Search,
  Settings2,
  Sparkles,
  Target,
} from "lucide-react";

export const navItems = [
  { id: "today", label: "Hoy", icon: Target },
  { id: "explore", label: "Explorar", icon: FileSearch },
  { id: "market", label: "Mercado", icon: BarChart3 },
  { id: "applications", label: "Aplicaciones", icon: BriefcaseBusiness },
  { id: "system", label: "Sistema", icon: Activity },
];

export function Sidebar({ view, setView }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">J2</div>
        <div>
          <strong>Job Searcher</strong>
          <span>Market Intelligence</span>
        </div>
      </div>
      <nav>
        {navItems.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={view === id ? "nav-item active" : "nav-item"}
            onClick={() => setView(id)}
          >
            <Icon size={17} />
            <span>{label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-foot">
        <Database size={15} />
        <span>SQLite local</span>
        <i />
      </div>
    </aside>
  );
}

export function Topbar({ query, setQuery, onSearch }) {
  return (
    <header className="topbar">
      <form
        className="global-search"
        onSubmit={(event) => {
          event.preventDefault();
          onSearch?.();
        }}
      >
        <Search size={17} />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Buscar roles, empresas, skills..."
        />
        <kbd>Enter</kbd>
      </form>
      <div className="topbar-actions">
        <span className="live-indicator"><i /> Datos locales</span>
        <button className="icon-button" aria-label="Configuración">
          <Settings2 size={18} />
        </button>
      </div>
    </header>
  );
}

export function Metric({ label, value, detail, tone = "default", icon: Icon = Gauge }) {
  return (
    <div className={`metric metric-${tone}`}>
      <div className="metric-label"><Icon size={15} />{label}</div>
      <strong>{value ?? "—"}</strong>
      <span>{detail}</span>
    </div>
  );
}

export function Score({ value, label, compact = false }) {
  const tone = value >= 78 ? "high" : value >= 55 ? "medium" : "low";
  return (
    <div className={`score score-${tone} ${compact ? "compact" : ""}`}>
      <strong>{value ?? "—"}</strong>
      {label && <span>{label}</span>}
    </div>
  );
}

export function JobTable({ jobs, selectedId, onSelect, loading }) {
  if (loading) return <div className="empty-state">Cargando oportunidades...</div>;
  if (!jobs.length) return <div className="empty-state">No hay resultados para estos filtros.</div>;
  return (
    <div className="job-table">
      <div className="job-table-head">
        <span>Puesto</span><span>Ubicación</span><span>Ajuste</span>
        <span>Aplicabilidad</span><span>Fuente</span><span>Estado</span>
      </div>
      {jobs.map((job) => {
        const evaluation = job.evaluation || {};
        const application = job.application || {};
        return (
          <button
            key={job.id}
            className={selectedId === job.id ? "job-row selected" : "job-row"}
            onClick={() => onSelect(job.id)}
          >
            <span className="job-primary">
              <b>{job.title}</b>
              <small><Building2 size={13} /> {job.company}</small>
            </span>
            <span className="job-location">
              <MapPin size={14} />
              <span>{job.location || "Sin ubicación"}</span>
            </span>
            <Score value={evaluation.priority_score} compact />
            <span className="feasibility">
              <i style={{ width: `${evaluation.application_feasibility || 0}%` }} />
              <b>{evaluation.application_feasibility ?? "—"}</b>
            </span>
            <span className={`source source-${job.source}`}>{job.source}</span>
            <span className={`status status-${application.status || "unreviewed"}`}>
              {application.status || "sin revisar"}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export function JobDetail({ job, onStatus }) {
  if (!job) {
    return (
      <aside className="detail-panel empty-detail">
        <CircleDot size={25} />
        <h3>Seleccioná una oportunidad</h3>
        <p>Vas a ver el razonamiento, la aplicabilidad y la evidencia.</p>
      </aside>
    );
  }
  const evaluation = job.evaluation || {};
  const dimensions = [
    ["Perfil", evaluation.profile_match],
    ["Técnico", evaluation.technical_match],
    ["Industria", evaluation.industry_match],
    ["Carrera", evaluation.career_value],
    ["Aplicabilidad", evaluation.application_feasibility],
  ];
  return (
    <aside className="detail-panel">
      <div className="detail-title">
        <div>
          <span className="eyebrow">{job.company}</span>
          <h2>{job.title}</h2>
          <p><MapPin size={14} /> {job.location || "Ubicación no informada"}</p>
        </div>
        <Score value={evaluation.priority_score} label="prioridad" />
      </div>
      <div className="detail-actions">
        <button className="primary" onClick={() => onStatus("applied")}>
          <Check size={16} /> Marcar aplicado
        </button>
        <button onClick={() => onStatus("saved")}>Guardar</button>
        <a href={job.source_url} target="_blank" rel="noreferrer" aria-label="Abrir oferta">
          <ExternalLink size={16} />
        </a>
      </div>
      <section>
        <h3>Lectura del puesto</h3>
        <p className="reason">{evaluation.reason || "Todavía no fue evaluado."}</p>
        <div className="dimension-list">
          {dimensions.map(([label, value]) => (
            <div key={label}>
              <span>{label}</span>
              <i><em style={{ width: `${value || 0}%` }} /></i>
              <b>{value ?? "—"}</b>
            </div>
          ))}
        </div>
      </section>
      <section>
        <h3>Señales a favor</h3>
        <ul className="evidence-list positive">
          {(evaluation.evidence_for || []).slice(0, 4).map((item) => <li key={item}>{item}</li>)}
          {!evaluation.evidence_for?.length && <li>Sin evidencia estructurada.</li>}
        </ul>
      </section>
      <section>
        <h3>Riesgos y faltantes</h3>
        <ul className="evidence-list negative">
          {(evaluation.evidence_against || []).slice(0, 4).map((item) => <li key={item}>{item}</li>)}
          {!evaluation.evidence_against?.length && <li>Sin riesgos estructurados.</li>}
        </ul>
      </section>
      <section>
        <h3>Skills detectadas</h3>
        <div className="skills">
          {(evaluation.skills || []).map((skill) => <span key={skill}>{skill}</span>)}
        </div>
      </section>
      {job.description && (
        <details>
          <summary>Descripción completa <ChevronRight size={15} /></summary>
          <div className="description">{job.description}</div>
        </details>
      )}
    </aside>
  );
}

export const metricIcons = {
  total: BriefcaseBusiness,
  priority: Sparkles,
  argentina: MapPin,
  recent: HeartPulse,
};
