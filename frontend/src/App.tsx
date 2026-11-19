import { useEffect, useState } from "react";

type NodeItem = { id: number; name: string; kind: string; criticality: number };
type EdgeItem = { id: number; source_id: number; target_id: number; criticality: number };

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function App() {
  const [nodes, setNodes] = useState<NodeItem[]>([]);
  const [edges, setEdges] = useState<EdgeItem[]>([]);
  const [status, setStatus] = useState("Conectando à API…");
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      fetch(`${API}/health`).then((r) => { if (!r.ok) throw new Error("API indisponível"); return r.json(); }),
      fetch(`${API}/api/v1/nodes`).then((r) => { if (!r.ok) throw new Error("Falha ao carregar nós"); return r.json(); }),
      fetch(`${API}/api/v1/edges`).then((r) => { if (!r.ok) throw new Error("Falha ao carregar dependências"); return r.json(); })
    ]).then(([, n, e]) => {
      setNodes(n); setEdges(e); setStatus("API operacional");
    }).catch((err: Error) => {
      setStatus("API desconectada"); setError(err.message);
    });
  }, []);

  return <main className="shell">
    <header><div className="brand-mark">O</div><div><p className="eyebrow">DIGITAL TWIN INTELLIGENCE</p><h1>ORACLE</h1></div><span className="status">{status}</span></header>
    <section className="intro"><p className="eyebrow">INFRASTRUCTURE OBSERVABILITY</p><h2>Entenda o impacto antes que a falha aconteça.</h2><p>Mapeie dependências e execute simulações determinísticas de impacto em ambientes controlados.</p></section>
    {error && <p className="error">{error}. Inicie a API em http://localhost:8000.</p>}
    <section className="metrics">
      <article><span>COMPONENTES</span><strong>{nodes.length}</strong><small>nós cadastrados</small></article>
      <article><span>DEPENDÊNCIAS</span><strong>{edges.length}</strong><small>relações mapeadas</small></article>
      <article><span>MOTOR</span><strong>v0.1</strong><small>análise determinística</small></article>
    </section>
    <section className="panel"><div className="panel-heading"><div><p className="eyebrow">TOPOLOGY INVENTORY</p><h3>Componentes da infraestrutura</h3></div><span>{nodes.length} registros</span></div>
      {nodes.length === 0 ? <p className="empty">Nenhum componente cadastrado. Utilize a API para adicionar os primeiros nós.</p> :
        <div className="table-wrap"><table><thead><tr><th>Nome</th><th>Tipo</th><th>Criticidade</th></tr></thead><tbody>
          {nodes.map((node) => <tr key={node.id}><td>{node.name}</td><td>{node.kind}</td><td>{Math.round(node.criticality * 100)}%</td></tr>)}
        </tbody></table></div>}
    </section>
    <footer>ORACLE · Foundation release 0.1.0 · Simulações não executam alterações na infraestrutura.</footer>
  </main>;
}
