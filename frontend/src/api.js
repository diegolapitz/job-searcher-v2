const json = async (url, options) => {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
};

export const api = {
  overview: () => json("/api/overview"),
  filterOptions: () => json("/api/filter-options"),
  jobs: (params = {}) => {
    const query = new URLSearchParams(
      Object.entries(params).filter(([, value]) => value !== "" && value != null),
    );
    return json(`/api/jobs?${query}`);
  },
  job: (id) => json(`/api/jobs/${id}`),
  updateApplication: (id, payload) =>
    json(`/api/jobs/${id}/application`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  trends: () => json("/api/market/trends"),
  skills: () => json("/api/market/skills"),
  runs: () => json("/api/system/runs"),
  sources: () => json("/api/system/sources"),
};
