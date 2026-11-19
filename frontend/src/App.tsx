import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

type NodeItem = { id: number; name: string; kind: string; criticality: number; capacity_units: number; current_load_units: number };
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
type CapacityComponent = { node_id: number; name: string; kind: string; capacity_units: number; current_load_units: number; projected_load_units: number; utilization_ratio: number; headroom_units: number; status: "normal" | "warning" | "over_capacity" };
type CapacityAssessment = { demand_multiplier: number; components_assessed: number; over_capacity: number; warnings: number; components: CapacityComponent[] };
type Telemetry = { id: number; node_id: number; metric: string; value: number; unit: string; observed_at: string };
type AuditEvent = { id: number; action: string; resource_type: string; resource_id: string; created_at: string };
type TopologySnapshotSummary = { id: number; tenant_id: string; version: number; node_count: number; edge_count: number; created_by: string; created_at: string };
type TopologySnapshotDetail = TopologySnapshotSummary & { nodes: NodeItem[]; edges: EdgeItem[] };

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const TENANT = import.meta.env.VITE_TENANT_ID;

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(TENANT ? { "X-Tenant-ID": TENANT } : {}),
      ...(sessionStorage.getItem("oracle-api-key")
        ? { "X-API-Key": sessionStorage.getItem("oracle-api-key") as string }
        : {}),
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

function TopologyGraph({ nodes, edges }: { nodes: NodeItem[]; edges: EdgeItem[] }) {
  const columns = Math.max(1, Math.min(4, nodes.length));
  const rows = Math.max(1, Math.ceil(nodes.length / columns));
  const width = columns * 235 + 20;
  const height = rows * 125 + 20;
  const positions = new Map<number, { x: number; y: number }>();
  nodes.forEach((node, index) => {
    positions.set(node.id, {
      x: 20 + (index % columns) * 235,
      y: 20 + Math.floor(index / columns) * 125,
    });
  });

  return (
    <div className="graph-frame">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Grafo de dependências da infraestrutura">
        <defs>
          <marker id="oracle-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L0,6 L7,3 z" fill="#70d9bd" />
          </marker>
        </defs>
        {edges.map((edge) => {
          const source = positions.get(edge.source_id);
          const target = positions.get(edge.target_id);
          if (!source || !target) return null;
          return (
            <line
              key={edge.id}
              x1={source.x + 95}
              y1={source.y + 35}
              x2={target.x + 95}
              y2={target.y + 35}
              stroke="#70d9bd"
              strokeOpacity="0.65"
              strokeWidth="2"
              markerEnd="url(#oracle-arrow)"
            />
          );
        })}
        {nodes.map((node) => {
          const point = positions.get(node.id);
          if (!point) return null;
          const label = node.name.length > 21 ? node.name.slice(0, 18) + "…" : node.name;
          return (
            <g key={node.id}>
              <rect x={point.x} y={point.y} width="190" height="70" rx="10" className="graph-node" />
              <text x={point.x + 13} y={point.y + 29} className="graph-node-label">{label}</text>
              <text x={point.x + 13} y={point.y + 50} className="graph-node-meta">
                {node.kind} · {Math.round(node.criticality * 100)}% criticidade
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default function App() {
  const [nodes, setNodes] = useState<NodeItem[]>([]);
  const [edges, setEdges] = useState<EdgeItem[]>([]);
  const [telemetry, setTelemetry] = useState<Telemetry[]>([]);
  const [capacity, setCapacity] = useState<CapacityAssessment | null>(null);
  const [demandMultiplier, setDemandMultiplier] = useState(1.0);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [snapshots, setSnapshots] = useState<TopologySnapshotSummary[]>([]);
  const [snapshotDetail, setSnapshotDetail] = useState<TopologySnapshotDetail | null>(null);
  const [snapshotBusy, setSnapshotBusy] = useState(false);
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [comparison, setComparison] = useState<ScenarioComparison | null>(null);
  const [aiExplanation, setAiExplanation] = useState("");
  const [aiBusy, setAiBusy] = useState(false);
  const [status, setStatus] = useState("Conectando à API…");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [apiCredential, setApiCredential] = useState(() => sessionStorage.getItem("oracle-api-key") ?? "");

  const refresh = useCallback(async () => {
    const [health, topology, samples, events, history, capacityResult] = await Promise.all([
      request<{ status: string }>("/health"),
      request<{ nodes: NodeItem[]; edges: EdgeItem[] }>("/api/v1/topology"),
      request<Telemetry[]>("/api/v1/telemetry?limit=8"),
      request<AuditEvent[]>("/api/v1/audit?limit=8").catch(() => [] as AuditEvent[]),
      request<TopologySnapshotSummary[]>("/api/v1/topology/snapshots?limit=10"),
      request<CapacityAssessment>(`/api/v1/capacity/assessment?demand_multiplier=${demandMultiplier}`),
    ]);
    setNodes(topology.nodes);
    setEdges(topology.edges);
    setTelemetry(samples);
    setCapacity(capacityResult);
    setAudit(events);
    setSnapshots(history);
    setStatus(health.status === "ok" ? "API operacional" : "API indisponível");
    setError("");
  }, [demandMultiplier]);

  useEffect(() => {
    refresh().catch((err: Error) => {
      setStatus("API desconectada");
      setError(err.message);
    });
  }, [refresh]);

  async function saveCredential(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = apiCredential.trim();
    if (value) sessionStorage.setItem("oracle-api-key", value);
    else sessionStorage.removeItem("oracle-api-key");
    setStatus("Validando credencial…");
    try {
      await refresh();
      setError("");
    } catch (err) {
      setStatus("Falha na autenticação");
      setError(err instanceof Error ? err.message : "Credencial inválida.");
    }
  }

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

  async function openSnapshot(snapshotId: number) {
    setSnapshotBusy(true);
    setError("");
    try {
      const detail = await request<TopologySnapshotDetail>(`/api/v1/topology/snapshots/${snapshotId}`);
      setSnapshotDetail(detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar versão da topologia.");
    } finally {
      setSnapshotBusy(false);
    }
  }

  async function exportAudit() {
    setError("");
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      const token = sessionStorage.getItem("oracle-api-key");
      if (token) headers["X-API-Key"] = token;
      if (TENANT) headers["X-Tenant-ID"] = TENANT;
      const response = await fetch(`${API}/api/v1/audit/export`, { headers });
      if (!response.ok) throw new Error(response.status === 403 ? "A exportação exige o papel admin." : `Falha ao exportar auditoria (HTTP ${response.status}).`);
      const file = await response.blob();
      const url = URL.createObjectURL(file);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "oracle-audit-export.json";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao exportar auditoria.");
    }
  }

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
        <form className="credential-form" onSubmit={saveCredential}>
          <input
            aria-label="Chave de API ORACLE"
            type="password"
            autoComplete="off"
            value={apiCredential}
            onChange={(event) => setApiCredential(event.target.value)}
            placeholder="Chave de API"
          />
          <button type="submit">Conectar</button>
        </form>
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

      <section className="panel capacity-panel">
        <div className="panel-heading">
          <div><p className="eyebrow">CAPACITY PLANNER</p><h3>Projeção de capacidade</h3></div>
          <label className="demand-select">Multiplicador de demanda
            <select value={demandMultiplier} onChange={(event) => setDemandMultiplier(Number(event.target.value))}>
              <option value="1">Base · 1,0×</option>
              <option value="1.1">Crescimento · 1,1×</option>
              <option value="1.25">Pico · 1,25×</option>
              <option value="1.5">Estresse · 1,5×</option>
              <option value="2">Extremo · 2,0×</option>
            </select>
          </label>
        </div>
        {capacity && <>
          <div className="capacity-summary">
            <span><strong>{capacity.components_assessed}</strong> componentes</span>
            <span><strong>{capacity.warnings}</strong> em alerta (≥80%)</span>
            <span><strong>{capacity.over_capacity}</strong> acima do limite (≥100%)</span>
          </div>
          {capacity.components.length === 0 ? <p className="empty">Cadastre componentes para projetar a capacidade.</p> :
            <div className="table-wrap"><table><thead><tr><th>Componente</th><th>Carga projetada</th><th>Capacidade</th><th>Utilização</th><th>Folga</th><th>Estado</th></tr></thead><tbody>
              {capacity.components.map((item) => <tr key={item.node_id}>
                <td>{item.name}</td>
                <td>{item.projected_load_units.toFixed(1)}</td>
                <td>{item.capacity_units.toFixed(1)}</td>
                <td>{(item.utilization_ratio * 100).toFixed(1)}%</td>
                <td>{item.headroom_units.toFixed(1)}</td>
                <td><span className={`capacity-state ${item.status}`}>{item.status === "normal" ? "Normal" : item.status === "warning" ? "Atenção" : "Sobrecarga"}</span></td>
              </tr>)}
            </tbody></table></div>}
        </>}
        <p className="graph-caption">Projeção determinística da carga declarada × multiplicador selecionado. Não presume failover, distribuição automática de tráfego ou capacidade não cadastrada.</p>
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
              capacity_units: Number(form.get("capacity_units")),
              current_load_units: Number(form.get("current_load_units")),
            }) });
            formElement.reset();
          });
          }}>
            <label>Nome<input name="name" required minLength={2} maxLength={120} pattern="[a-zA-Z0-9][a-zA-Z0-9._-]*" placeholder="payments-api" /></label>
            <label>Tipo<select name="kind"><option value="service">Serviço</option><option value="database">Banco de dados</option><option value="queue">Fila</option><option value="api">API</option><option value="worker">Worker</option><option value="cache">Cache</option><option value="gateway">Gateway</option><option value="other">Outro</option></select></label>
            <label>Criticidade<select name="criticality"><option value="0.25">Baixa · 25%</option><option value="0.5" selected>Média · 50%</option><option value="0.75">Alta · 75%</option><option value="1">Crítica · 100%</option></select></label>
            <label>Capacidade nominal<input name="capacity_units" type="number" min="0.01" step="any" defaultValue="100" required /></label>
            <label>Carga atual<input name="current_load_units" type="number" min="0" step="any" defaultValue="0" required /></label>
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
        <div className="panel-heading"><div><p className="eyebrow">LIVE TOPOLOGY</p><h3>Mapa visual de dependências</h3></div><span>{nodes.length} nós · {edges.length} ligações</span></div>
        {nodes.length === 0 ? <p className="empty">Adicione componentes para construir o mapa da infraestrutura.</p> :
          <>
            <TopologyGraph nodes={nodes} edges={edges} />
            <p className="graph-caption">As setas apontam do componente consumidor para o serviço ou recurso do qual ele depende.</p>
          </>}
      </section>

      <section className="panel">
        <div className="panel-heading"><div><p className="eyebrow">TEMPORAL TOPOLOGY</p><h3>Histórico de versões do grafo</h3></div><span>{snapshots.length} versões recentes</span></div>
        {snapshots.length === 0 ? <p className="empty">O histórico será criado automaticamente quando componentes ou dependências forem cadastrados.</p> :
          <div className="snapshot-list">
            {snapshots.map((snapshot) => (
              <button
                type="button"
                key={snapshot.id}
                className={snapshotDetail?.id === snapshot.id ? "snapshot-item active" : "snapshot-item"}
                onClick={() => openSnapshot(snapshot.id)}
                disabled={snapshotBusy}
              >
                <strong>Versão {snapshot.version}</strong>
                <span>{snapshot.node_count} nós · {snapshot.edge_count} ligações</span>
                <small>{new Date(snapshot.created_at).toLocaleString("pt-BR")}</small>
              </button>
            ))}
          </div>}
        {snapshotDetail && <div className="snapshot-detail">
          <p className="eyebrow">SNAPSHOT #{snapshotDetail.id} · VERSÃO {snapshotDetail.version}</p>
          <p className="graph-caption">Estado histórico somente para consulta. Visualizar uma versão não restaura nem altera a topologia atual.</p>
          <TopologyGraph nodes={snapshotDetail.nodes} edges={snapshotDetail.edges} />
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
          <div className="panel-heading"><div><p className="eyebrow">GOVERNANCE</p><h3>Auditoria recente</h3></div><button className="secondary-button export-button" onClick={exportAudit}>Exportar JSON</button></div>
          {audit.length === 0 ? <p className="empty">Nenhum evento registrado.</p> :
            <div className="event-list">{audit.map((event) => <div className="event" key={event.id}><strong>{event.action}</strong><span>{event.resource_type} #{event.resource_id}</span></div>)}</div>}
        </article>
      </section>

      <footer>ORACLE · Foundation 0.4.0 · Simulações e snapshots históricos são somente leitura e não executam alterações na infraestrutura. OIDC/SSO e revisão de produção permanecem pendentes.</footer>
    </main>
  );
}
