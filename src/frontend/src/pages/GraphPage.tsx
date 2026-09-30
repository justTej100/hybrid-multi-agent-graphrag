import { useEffect, useState } from 'react';
import { getGraph, type GraphEdge, type GraphNode } from '../api';
import PdfViewer from '../components/PdfViewer';

export default function GraphPage() {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [error, setError] = useState('');
  const [pdfDocId, setPdfDocId] = useState<string | null>(null);
  const [pdfPage, setPdfPage] = useState(1);

  useEffect(() => {
    getGraph()
      .then((graph) => {
        setEnabled(graph.enabled);
        setNodes(graph.nodes ?? []);
        setEdges(graph.edges ?? []);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load the graph'));
  }, []);

  function openBook(bookId: string | null | undefined, page: number | null | undefined) {
    if (!bookId) return;
    setPdfDocId(bookId);
    setPdfPage(page && page > 0 ? page : 1);
  }

  return (
    <div className="study-grid">
      <div className="study-col">
        <h1 className="page-title">Knowledge graph</h1>
        {enabled === false && <p className="empty">The graph is off. It turns on when Neo4j is configured.</p>}
        {error && <p className="upload-msg" style={{ color: 'var(--danger)' }}>{error}</p>}
        {enabled && nodes.length === 0 && edges.length === 0 && <p className="empty">No entities stored yet.</p>}
        {nodes.length > 0 && (
          <div className="graph-nodes">
            {nodes.map((node) => (
              <button
                key={`${node.name}-${node.page_number ?? 0}`}
                type="button"
                className="graph-node"
                onClick={() => openBook(node.book_id, node.page_number)}
              >
                <strong>{node.name}</strong>
                {node.type ? <span>{node.type}</span> : null}
                {node.page_number ? <span>p{node.page_number}</span> : null}
              </button>
            ))}
          </div>
        )}
        {edges.length > 0 && (
          <div className="graph-edges">
            {edges.map((edge, index) => (
              <button
                key={`${edge.source}-${edge.relationship}-${edge.target}-${index}`}
                type="button"
                className="graph-edge"
                onClick={() => openBook(edge.book_id, edge.page_number)}
              >
                <span className="graph-entity">{edge.source}</span>
                <span className="graph-rel">{edge.relationship}</span>
                <span className="graph-entity">{edge.target}</span>
                {edge.evidence && <p className="source-excerpt">{edge.evidence}</p>}
                {edge.page_number ? <span className="cite-chip">p{edge.page_number}</span> : null}
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="study-col">
        <div className="panel pdf-panel">
          <div className="section-label">Textbook</div>
          {pdfDocId ? <PdfViewer documentId={pdfDocId} page={pdfPage} /> : <p className="empty">A page citation opens the textbook here.</p>}
        </div>
      </div>
    </div>
  );
}
