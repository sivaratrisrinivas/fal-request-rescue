import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

type CaseRow = {
  id: string;
  created_at: string;
  endpoint_id: string;
  schema_version: string;
  status: string;
  disposition: string | null;
};

type Evidence = {
  id: string;
  kind: string;
  source: string;
  captured_at: string;
  redacted_content: unknown;
  digest: string;
};

type CaseDetail = {
  id: string;
  created_at: string;
  endpoint_id: string;
  schema_version: string;
  report: string;
  payload: Record<string, unknown>;
  status: string;
  replay: boolean;
  origin: string;
  disposition: string | null;
  evidence: Evidence[];
};

type Finding = { category: string; observed_fact: string; confidence: string };
type SchemaError = { field: string; code: string; message: string; allowed?: unknown[] };
type InvestigateOut = {
  schema_snapshot: { version: string; known: boolean; stale: boolean };
  schema_errors: SchemaError[];
  queue: { request_id: string; status: string; verdict: string }[];
  webhook: { present: boolean; verified: boolean; reason: string };
  findings: Finding[];
  diagnostics_used: string[];
};
type DispositionOut = {
  disposition: string;
  confidence: string;
  uncertainty: string;
  missing?: string[];
  corrected_payload?: Record<string, unknown>;
  packet?: Record<string, unknown>;
};
type AuditEvent = { actor: string; event_type: string; timestamp: string };
type ReplayOut = {
  mode: string; badge: string; fixture_source: string;
  submitted_at: string; completed_at: string; disposition: string;
};

const API = "";
const badge: React.CSSProperties = { border: "1px solid #999", borderRadius: 4, padding: "2px 8px" };

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return (await r.json()) as T;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return (await r.json()) as T;
}

function Diff({ before, after }: { before: Record<string, unknown>; after: Record<string, unknown> }) {
  const keys = [...new Set([...Object.keys(before), ...Object.keys(after)])];
  return (
    <table>
      <thead><tr><th>field</th><th>before</th><th>after</th></tr></thead>
      <tbody>
        {keys.map((k) => {
          const changed = JSON.stringify(before[k]) !== JSON.stringify(after[k]);
          return (
            <tr key={k} style={changed ? { background: "#fff8dc" } : undefined}>
              <td><code>{k}</code></td>
              <td><code>{JSON.stringify(before[k])}</code></td>
              <td><code>{JSON.stringify(after[k])}</code></td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function Detail({ id, back }: { id: string; back: () => void }) {
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [inv, setInv] = useState<InvestigateOut | null>(null);
  const [disp, setDisp] = useState<DispositionOut | null>(null);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [draft, setDraft] = useState<string | null>(null);
  const [actor, setActor] = useState("analyst");
  const [replay, setReplay] = useState<ReplayOut | null>(null);
  const [liveMsg, setLiveMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setError(null);
      const d = await get<CaseDetail>(`/cases/${id}`);
      setDetail(d);
      setInv(await post<InvestigateOut>(`/cases/${id}/investigate`, {}));
      if (d.disposition) {
        setDisp(await post<DispositionOut>(`/cases/${id}/disposition`, {}));
        try {
          const dr = await get<{ draft: string }>(`/cases/${id}/customer-draft`);
          setDraft(dr.draft);
        } catch { setDraft(null); }
      }
      const h = await get<{ audit: AuditEvent[] }>(`/cases/${id}/history`);
      setAudit(h.audit);
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => { void load(); }, [id]);

  async function runDisposition() {
    await post(`/cases/${id}/disposition`, {});
    await load();
  }

  async function approve(actionType: string) {
    await post(`/cases/${id}/approve`, { action_type: actionType, actor });
    await load();
  }

  async function runReplay() {
    setReplay(await post<ReplayOut>(`/cases/${id}/replay`, {}));
    await load();
  }

  async function runLiveTest() {
    setLiveMsg(null);
    try {
      const out = await post<{ result: Record<string, unknown> }>(`/cases/${id}/live-test`, { mode: "live" });
      setLiveMsg(`Live submitted: ${JSON.stringify(out.result)}`);
    } catch (e) {
      setLiveMsg(`Live blocked: ${e}`);
    }
    await load();
  }

  function downloadExport() {
    window.open(`${API}/cases/${id}/export`, "_blank");
  }

  if (error) return <main><p role="alert" style={{ color: "crimson" }}>{error}</p><button onClick={back}>Back</button></main>;
  if (!detail || !inv) return <main><p>Loading…</p></main>;

  return (
    <main style={{ fontFamily: "system-ui", maxWidth: 860, margin: "2rem auto", padding: "0 1rem" }}>
      <button onClick={back}>← Inbox</button>{" "}
      {detail.replay
        ? <span style={badge}>replay · synthetic fixture — not a live fal request</span>
        : <span style={{ ...badge, borderColor: "crimson" }}>live fal request</span>}
      <h1>{detail.id}</h1>
      <p>{detail.endpoint_id}@{detail.schema_version} — {detail.status} — disposition: {detail.disposition ?? "none yet"}</p>
      <p>Origin: <code>{detail.origin}</code></p>
      <p><strong>Report:</strong> {detail.report}</p>

      <h2>Replay / live</h2>
      <button onClick={runReplay}>Run replay</button>{" "}
      <button onClick={runLiveTest}>Live test (capped, needs approval)</button>
      {replay && <p><span style={badge}>{replay.badge}</span> source <code>{replay.fixture_source}</code> → {replay.disposition} ({replay.submitted_at} – {replay.completed_at})</p>}
      {liveMsg && <p>{liveMsg}</p>}

      <h2>Schema errors ({inv.schema_errors.length})</h2>
      <ul>{inv.schema_errors.map((e, i) => <li key={i}><code>{e.field}</code> [{e.code}] {e.message}</li>)}</ul>

      <h2>Queue</h2>
      <ul>{inv.queue.map((q) => <li key={q.request_id}><code>{q.request_id}</code> {q.status}: {q.verdict}</li>)}</ul>
      {inv.webhook.present && <p><strong>Webhook:</strong> verified={String(inv.webhook.verified)} — {inv.webhook.reason}</p>}

      <h2>Diagnosis</h2>
      {disp
        ? <>
          <p>{disp.disposition} (confidence {disp.confidence}) — {disp.uncertainty}</p>
          {disp.missing && <ul>{disp.missing.map((m) => <li key={m}>{m}</li>)}</ul>}
          {disp.corrected_payload && <Diff before={detail.payload} after={disp.corrected_payload} />}
          {disp.packet && <details><summary>Escalation packet</summary><pre>{JSON.stringify(disp.packet, null, 2)}</pre></details>}
        </>
        : <button onClick={runDisposition}>Run disposition</button>}

      <h2>Evidence</h2>
      <ul>
        {detail.evidence.map((e) => (
          <li key={e.id}><code>{e.kind}</code> {e.source} <code>{e.digest.slice(0, 12)}</code>
            <details><summary>content</summary><pre>{JSON.stringify(e.redacted_content, null, 2)}</pre></details>
          </li>
        ))}
      </ul>

      <h2>Customer draft (preview — approval required before sending)</h2>
      {draft ? <pre>{draft}</pre> : <p>No draft yet — run disposition first.</p>}

      <h2>Approvals</h2>
      <label>Actor <input value={actor} onChange={(e) => setActor(e.target.value)} /></label>{" "}
      <button onClick={() => approve("disposition")}>Approve correction</button>{" "}
      <button onClick={() => approve("live-test")}>Approve paid run</button>{" "}
      <button onClick={() => approve("customer-text")}>Approve customer text</button>{" "}
      <button onClick={downloadExport}>Export case JSON</button>

      <h2>Timeline</h2>
      <ul>{audit.map((a, i) => <li key={i}>{a.timestamp} — {a.actor} — {a.event_type}</li>)}</ul>
    </main>
  );
}

function App() {
  const [cases, setCases] = useState<CaseRow[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [report, setReport] = useState("");
  const [endpointId, setEndpointId] = useState("fal-ai/flux/schnell");
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      setError(null);
      const body = await get<{ data: CaseRow[] }>("/cases?page=1&pageSize=20");
      setCases(body.data ?? []);
    } catch (e) {
      setError(`Backend unreachable at :8000 — start it first. ${e}`);
    }
  }

  useEffect(() => { void refresh(); }, []);

  async function createCase(e: React.FormEvent) {
    e.preventDefault();
    await post("/cases", {
      endpoint_id: endpointId, schema_version: "v1", report,
      payload: { prompt: report.slice(0, 200) || "demo prompt" },
    });
    setReport("");
    await refresh();
  }

  if (selected) return <Detail id={selected} back={() => { setSelected(null); void refresh(); }} />;

  return (
    <main style={{ fontFamily: "system-ui", maxWidth: 760, margin: "2rem auto", padding: "0 1rem" }}>
      <h1>fal Request Rescue</h1>
      <p><span style={badge}>replay mode</span> No credentials required. Synthetic fixtures only — never live fal traffic.</p>
      {error && <p role="alert" style={{ color: "crimson" }}>{error}</p>}
      <form onSubmit={createCase}>
        <input value={endpointId} onChange={(e) => setEndpointId(e.target.value)} aria-label="endpoint id" style={{ width: "100%", marginBottom: 8 }} />
        <textarea value={report} onChange={(e) => setReport(e.target.value)} placeholder="Customer report (sanitized — no keys)" rows={3} style={{ width: "100%" }} />
        <button type="submit">Create case</button>
      </form>
      <h2>Inbox ({cases.length})</h2>
      <ul>
        {cases.map((c) => (
          <li key={c.id}>
            <button onClick={() => setSelected(c.id)}>{c.id}</button>{" "}
            {c.endpoint_id}@{c.schema_version} — {c.disposition ?? "no disposition"}
          </li>
        ))}
      </ul>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
