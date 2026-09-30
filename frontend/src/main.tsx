import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

type CaseRow = {
  id: string;
  created_at: string;
  endpoint_id: string;
  schema_version: string;
  status: string;
};

const API = "";

function App() {
  const [cases, setCases] = useState<CaseRow[]>([]);
  const [report, setReport] = useState("");
  const [endpointId, setEndpointId] = useState("fal-ai/flux/schnell");
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setError(null);
    try {
      const r = await fetch(`${API}/cases?page=1&pageSize=20`);
      const body = await r.json();
      setCases(body.data ?? []);
    } catch (e) {
      setError(`Backend unreachable at :8000 — start it first. ${e}`);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function createCase(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const r = await fetch(`${API}/cases`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        endpoint_id: endpointId,
        schema_version: "v1",
        report,
        payload: {prompt: report.slice(0, 200) || "demo prompt"},
      }),
    });
    if (!r.ok) {
      setError(`Create failed: ${await r.text()}`);
      return;
    }
    setReport("");
    await refresh();
  }

  return (
    <main style={{fontFamily: "system-ui", maxWidth: 760, margin: "2rem auto", padding: "0 1rem"}}>
      <h1>fal Request Rescue</h1>
      <p>
        <span style={{border: "1px solid #999", borderRadius: 4, padding: "2px 8px"}}>replay mode</span>{" "}
        No credentials required. Synthetic fixtures only.
      </p>
      {error && <p role="alert" style={{color: "crimson"}}>{error}</p>}
      <form onSubmit={createCase}>
        <input
          value={endpointId}
          onChange={(e) => setEndpointId(e.target.value)}
          aria-label="endpoint id"
          style={{width: "100%", marginBottom: 8}}
        />
        <textarea
          value={report}
          onChange={(e) => setReport(e.target.value)}
          placeholder="Customer report (sanitized — no keys)"
          rows={3}
          style={{width: "100%"}}
        />
        <button type="submit">Create case</button>
      </form>
      <h2>Inbox ({cases.length})</h2>
      <ul>
        {cases.map((c) => (
          <li key={c.id}>
            {c.id} — {c.endpoint_id}@{c.schema_version} — {c.status}
          </li>
        ))}
      </ul>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
