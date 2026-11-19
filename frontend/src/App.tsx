import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

type NodeItem = { id: number; name: string; kind: string; criticality: number };
type EdgeItem = { id: number; source_id: number; target_id: number; criticality: number };
type ImpactedNode = { node_id: number; name: string; hop_distance: number; impact_score: number };
type ScenarioComparison = {
  scenario_a: Simulation;
  scenario_b: Simulation;
  newly_impacted_in_a: number[];
  newly_impacted_in_b: number[];
  shared_impacted: number[];
  impact_score_deltas: { node_id: number; name: string; score_a: number; score_b: number; delta: number }[];
};
type Simulation = {
  simulation_id: number | null;
  failed_node_id: number;
  failure_mode: string;
  impacted_nodes: ImpactedNode[];
  total_impacted: number;
  methodology: string;
};
type Telemetry = { id: number; node_id: number; metric: string; value: number; unit: string; observed_at: string };
type AuditEvent = { id: number; action: string; resource_type: string; resource_id: string; created_at: string };

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const TENANT = import.meta.env.VITE_TENANT_ID ?? "default";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Tenant-ID": TENANT,
      ...options.headers,
    },
  });
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      message = typeof body.detail === "string" ? body.detail : message;
    } catch {
      // Keep the HTTP status as the fallback error message.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export default function App() {
  const [nodes, setNodes] = useState<NodeItem[]>([]);
  const [edges, setEdges] = useState<EdgeItem[]>([]);
  const [telemetry, setTelemetry] = useState<Telemetry[]>([]);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [comparison, setComparison] = useState<ScenarioComparison | null>(null);
  const [aiExplanation, setAiExplanation] = useState("");
  const [aiBusy, setAiBusy] = useState(false);
  const [status, setStatus] = useState("Conectando à API…");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const [health, topology, samples, events] = await Promise.all([
      request<{ status: string }>("/health"),
      request<{ nodes: NodeItem[]; edges: EdgeItem[] }>("/api/v1/topology"),
      request<Telemetry[]>("/api/v1/telemetry?limit=8"),
      request<AuditEvent[]>("/api/v1/audit?limit=8"),
    ]);
    setNodes(topology.nodes);
    setEdges(topology.edges);
    setTelemetry(samples);
    setAudit(events);
    setStatus(health.status === "ok" ? "API operacional" : "API indisponível");
    setError("");
  }, []);

  useEffect(() => {
    refresh().catch((err: Error) => {
      setStatus("API desconectada");
      setError(err.message);
    });
  }, [refresh]);

  async function submit(
    event: FormEvent<HTMLFormElement>,
    action: () => Promise<unknown>,
  ) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await action();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha inesperada.");
    } finally {
      setBusy(false);
    }
  }

  const nodeName = (id: number) => nodes.find((node) => node.id === id)?.name ?? "#" + id;

  async function explainWithAI() {
    if (!simulation?.simulation_id) return;
    setAiBusy(true);
    setAiExplanation("");
    setError("");
    try {
      const result = await request<{ explanation: string }>("/api/v1/ai/explain", {
        method: "POST",
        body: JSON.stringify({ simulation_id: simulation.simulation_id }),
      });
      setAiExplanation(result.explanation);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao gerar explicação com IA.");
    } finally {
      setAiBusy(false);
    }
  }

  return (
    <main className="shell">
      <header>
        <div className="brand-mark">O</div>
        <div><p className="eyebrow">DIGITAL TWIN INTELLIGENCE</p><h1>ORACLE</h1></div>
        <span className="status">{status}</span>
      </header>

      <section className="intro">
        <p className="eyebrow">INFRASTRUCTURE OBSERVABILITY</p>
        <h2>Entenda o impacto antes que a falha aconteça.</h2>
        <p>Modele dependências, acompanhe sinais operacionais e simule falhas sem alterar a infraestrutura real.</p>
      </section>

      {error && <p className="error" role="alert">{error}. Confira a API em http://localhost:8000.</p>}

      <section className="metrics">
        <article><span>COMPONENTES</span><strong>{nodes.length}</strong><small>nós cadastrados</small></article>
        <article><span>DEPENDÊNCIAS</span><strong>{edges.length}</strong><small>relações mapeadas</small></article>
        <article><span>TELEMETRIA</span><strong>{telemetry.length}</strong><small>amostras recentes</small></article>
      </section>

      <section className="workspace">
        <article className="panel">
          <div className="panel-heading"><div><p className="eyebrow">INVENTORY</p><h3>Novo componente</h3></div></div>
          <form className="editor-form" onSubmit={(event) => {
            const formElement = event.currentTarget;
            return submit(event, async () => {
            const form = new FormData(formElement);
            await request("/api/v1/nodes", { method: "POST", body: JSON.stringify({
              name: String(form.get("name")),
              kind: String(form.get("kind")),
              criticality: Number(form.get("criticality")),
            }) });
            formElement.reset();
          });
          }}>
            <label>Nome<input name="name" required minLength={2} maxLength={120} pattern="[a-zA-Z0-9][a-zA-Z0-9._-]*" placeholder="payments-api" /></label>
            <label>Tipo<select name="kind"><option value="service">Serviço</option><option value="database">Banco de dados</option><option value="queue">Fila</option><option value="api">API</option><option value="worker">Worker</option><option value="cache">Cache</option><option value="gateway">Gateway</option><option value="other">Outro</option></select></label>
            <label>Criticidade<select name="criticality"><option value="0.25">Baixa · 25%</option><option value="0.5" selected>Média · 50%</option><option value="0.75">Alta · 75%</option><option value="1">Crítica · 100%</option></select></label>
            <button disabled={busy || status !== "API operacional"}>Adicionar componente</button>
          </form>
        </article>

        <article className="panel">
          <div className="panel-heading"><div><p className="eyebrow">DEPENDENCY GRAPH</p><h3>Nova dependência</h3></div></div>
          <form className="editor-form" onSubmit={(event) => {
          const formElement = event.currentTarget;
          return submit(event, async () => {
            const form = new FormData(formElement);
            await request("/api/v1/edges", { method: "POST", body: JSON.stringify({
              source_id: Number(form.get("source_id")),
              target_id: Number(form.get("target_id")),
              criticality: Number(form.get("criticality")),
            }) });
          });
          }}>
            <label>Consumidor<select name="source_id" required>{nodes.map((node) => <option key={node.id} value={node.id}>{node.name}</option>)}</select></label>
            <label>Dependência<select name="target_id" required>{nodes.map((node) => <option key={node.id} value={node.id}>{node.name}</option>)}</select></label>
            <label>Criticidade da relação<select name="criticality"><option value="0.5">Média</option><option value="0.75">Alta</option><option value="1">Crítica</option></select></label>
            <button disabled={busy || nodes.length < 2 || status !== "API operacional"}>Criar dependência</button>
          </form>
        </article>
      </section>

      <section className="panel">
        <div className="panel-heading"><div><p className="eyebrow">FAILURE LAB</p><h3>Simular indisponibilidade</h3></div></div>
        <form className="simulation-form" onSubmit={(event) => {
          const formElement = event.currentTarget;
          return submit(event, async () => {
          const form = new FormData(formElement);
          const result = await request<Simulation>("/api/v1/simulations", { method: "POST", body: JSON.stringify({
            failed_node_id: Number(form.get("failed_node_id")),
            failure_mode: String(form.get("failure_mode")),
          }) });
          setSimulation(result);
          setAiExplanation("");
        });
        }}>
          <label>Componente afetado<select name="failed_node_id" required>{nodes.map((node) => <option key={node.id} value={node.id}>{node.name}</option>)}</select></label>
          <label>Modo de falha<select name="failure_mode"><option value="unavailable">Indisponível</option><option value="degraded">Degradado</option></select></label>
          <button disabled={busy || nodes.length === 0 || status !== "API operacional"}>Executar simulação</button>
        </form>
        {simulation && <div className="result">
          <p className="eyebrow">SIMULAÇÃO #{simulation.simulation_id}</p>
          <h4>{simulation.total_impacted} componente(s) potencialmente impactado(s)</h4>
          <button className="secondary-button" onClick={explainWithAI} disabled={aiBusy}>
            {aiBusy ? "Analisando…" : "Explicar resultado com DeepSeek"}
          </button>
          {aiExplanation && <div className="ai-explanation"><p className="eyebrow">ANÁLISE ASSISTIDA POR IA</p><p>{aiExplanation}</p><small>Confira as conclusões com um especialista antes de tomar decisões operacionais.</small></div>}
          {simulation.impacted_nodes.length === 0 ? <p className="empty">Nenhum consumidor foi identificado no grafo atual.</p> :
            <div className="table-wrap"><table><thead><tr><th>Componente</th><th>Saltos</th><th>Impacto estimado</th></tr></thead><tbody>
              {simulation.impacted_nodes.map((item) => <tr key={item.node_id}><td>{item.name}</td><td>{item.hop_distance}</td><td>{(item.impact_score * 100).toFixed(1)}%</td></tr>)}
            </tbody></table></div>}
          <small>{simulation.methodology}</small>
        </div>}
      </section>

      <section className="panel">
        <div className="panel-heading"><div><p className="eyebrow">SCENARIO COMPARISON</p><h3>Comparar dois cenários de falha</h3></div></div>
        <form className="simulation-form compare-form" onSubmit={(event) => {
          const formElement = event.currentTarget;
          return submit(event, async () => {
            const form = new FormData(formElement);
            const result = await request<ScenarioComparison>("/api/v1/scenarios/compare", {
              method: "POST",
              body: JSON.stringify({
                scenario_a: {
                  failed_node_id: Number(form.get("failed_a")),
                  failure_mode: String(form.get("mode_a")),
                },
                scenario_b: {
                  failed_node_id: Number(form.get("failed_b")),
                  failure_mode: String(form.get("mode_b")),
                },
              }),
            });
            setComparison(result);
          });
        }}>
          <label>Falha no cenário A<select name="failed_a" required>{nodes.map((node) => <option key={node.id} value={node.id}>{node.name}</option>)}</select></label>
          <label>Modo A<select name="mode_a"><option value="unavailable">Indisponível</option><option value="degraded">Degradado</option></select></label>
          <label>Falha no cenário B<select name="failed_b" required>{nodes.map((node) => <option key={node.id} value={node.id}>{node.name}</option>)}</select></label>
          <label>Modo B<select name="mode_b"><option value="unavailable">Indisponível</option><option value="degraded">Degradado</option></select></label>
          <button disabled={busy || nodes.length === 0 || status !== "API operacional"}>Comparar cenários</button>
        </form>
        {comparison && <div className="result">
          <div className="comparison-summary">
            <span><strong>{comparison.scenario_a.total_impacted}</strong> impactos no cenário A</span>
            <span><strong>{comparison.scenario_b.total_impacted}</strong> impactos no cenário B</span>
          </div>
          <p className="comparison-line"><strong>Exclusivos de A:</strong> {comparison.newly_impacted_in_a.map(nodeName).join(", ") || "nenhum"}</p>
          <p className="comparison-line"><strong>Exclusivos de B:</strong> {comparison.newly_impacted_in_b.map(nodeName).join(", ") || "nenhum"}</p>
          <p className="comparison-line"><strong>Compartilhados:</strong> {comparison.shared_impacted.map(nodeName).join(", ") || "nenhum"}</p>
          <div className="table-wrap"><table><thead><tr><th>Componente</th><th>Pontuação A</th><th>Pontuação B</th><th>Diferença B−A</th></tr></thead><tbody>
            {comparison.impact_score_deltas.map((item) => <tr key={item.node_id}><td>{item.name}</td><td>{(item.score_a * 100).toFixed(1)}%</td><td>{(item.score_b * 100).toFixed(1)}%</td><td>{(item.delta * 100).toFixed(1)} p.p.</td></tr>)}
          </tbody></table></div>
        </div>}
      </section>

      <section className="panel">
        <div className="panel-heading"><div><p className="eyebrow">TOPOLOGY INVENTORY</p><h3>Componentes e dependências</h3></div><span>{nodes.length} nós · {edges.length} relações</span></div>
        {nodes.length === 0 ? <p className="empty">Nenhum componente cadastrado. Adicione o primeiro acima.</p> :
          <div className="table-wrap"><table><thead><tr><th>Nome</th><th>Tipo</th><th>Criticidade</th><th>Dependências</th></tr></thead><tbody>
            {nodes.map((node) => <tr key={node.id}><td>{node.name}</td><td>{node.kind}</td><td>{Math.round(node.criticality * 100)}%</td><td>{edges.filter((edge) => edge.source_id === node.id).map((edge) => nodeName(edge.target_id)).join(", ") || "—"}</td></tr>)}
          </tbody></table></div>}
      </section>

      <section className="workspace">
        <article className="panel">
          <div className="panel-heading"><div><p className="eyebrow">OBSERVABILITY</p><h3>Telemetria recente</h3></div></div>
          {telemetry.length === 0 ? <p className="empty">Nenhuma amostra recebida. Use POST /api/v1/telemetry.</p> :
            <div className="table-wrap"><table><thead><tr><th>Componente</th><th>Métrica</th><th>Valor</th></tr></thead><tbody>
              {telemetry.map((item) => <tr key={item.id}><td>{nodeName(item.node_id)}</td><td>{item.metric}</td><td>{item.value} {item.unit}</td></tr>)}
            </tbody></table></div>}
        </article>
        <article className="panel">
          <div className="panel-heading"><div><p className="eyebrow">GOVERNANCE</p><h3>Auditoria recente</h3></div></div>
          {audit.length === 0 ? <p className="empty">Nenhum evento registrado.</p> :
            <div className="event-list">{audit.map((event) => <div className="event" key={event.id}><strong>{event.action}</strong><span>{event.resource_type} #{event.resource_id}</span></div>)}</div>}
        </article>
      </section>

      <footer>ORACLE · Foundation 0.2.0 · Simulações são análises e não executam alterações na infraestrutura. Isolamento multi-tenant completo ainda não está habilitado.</footer>
    </main>
  );
}
