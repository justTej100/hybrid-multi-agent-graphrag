import { FormEvent, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { chat, getSession, listDocuments, listSessions } from '../api';
import AnswerBlock from '../components/AnswerBlock';
import PdfViewer from '../components/PdfViewer';
import { useMe } from '../me';
import type { ChatMessage, Document, Scope, Source } from '../types';

type Turn = ChatMessage & { sources?: Source[] };

export default function StudyPage() {
  const me = useMe();
  const [searchParams] = useSearchParams();
  const initialDoc = searchParams.get('document');
  const incoming = searchParams.get('q');
  const [docs, setDocs] = useState<Document[]>([]);
  const [scopeType, setScopeType] = useState<'library' | 'document'>(initialDoc ? 'document' : 'library');
  const [documentId, setDocumentId] = useState(initialDoc ?? '');
  const [messages, setMessages] = useState<Turn[]>([]);
  const [prompt, setPrompt] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [pdfDocId, setPdfDocId] = useState<string | null>(null);
  const [pdfPage, setPdfPage] = useState(1);
  const [pdfTitle, setPdfTitle] = useState('');
  const sessionId = useRef<string | null>(null);
  const started = useRef<string | null>(null);

  useEffect(() => {
    listDocuments()
      .then((list) => {
        setDocs(list.filter((doc) => doc.status === 'ready'));
        if (initialDoc) setDocumentId(initialDoc);
      })
      .catch(() => setDocs([]));
  }, [initialDoc]);

  function scope(): Scope {
    if (scopeType === 'document' && documentId) return { type: 'document', document_id: documentId };
    return { type: 'library' };
  }

  function openPdf(source: Source | undefined, page?: number) {
    if (!source) return;
    setPdfDocId(source.document_id);
    setPdfPage(page ?? source.page_number);
    setPdfTitle(source.document_title || 'Source');
  }

  async function ask(question: string, continueSession: boolean, prior?: Turn[]) {
    const trimmed = question.trim();
    if (!trimmed || busy) return;
    const history: Turn[] = [...(prior ?? messages), { role: 'user', content: trimmed }];
    setMessages(history);
    setPrompt('');
    setBusy(true);
    setError('');
    try {
      const response = await chat(
        history.map(({ role, content }) => ({ role, content })),
        'chat',
        scope(),
        false,
        continueSession ? sessionId.current : null,
      );
      const saved = response.meta.session_id;
      if (typeof saved === 'string') sessionId.current = saved;
      const sources = response.sources ?? [];
      setMessages([...history, { role: 'assistant', content: response.brief, sources }]);
      openPdf(sources[0]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chat failed');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (incoming) {
      if (started.current === `q:${incoming}`) return;
      started.current = `q:${incoming}`;
      sessionId.current = null;
      setMessages([]);
      void ask(incoming, false, []);
      return;
    }
    if (!me?.is_admin || started.current) return;
    started.current = 'resume';
    listSessions()
      .then((sessions) => (sessions[0] ? getSession(sessions[0].id) : null))
      .then((session) => {
        if (!session) return;
        sessionId.current = session.id;
        const turns: Turn[] = session.messages.map((message) => ({
          role: message.role,
          content: message.content,
          sources: message.sources ?? undefined,
        }));
        setMessages(turns);
        const last = [...turns].reverse().find((turn) => turn.role === 'assistant' && turn.sources?.length);
        openPdf(last?.sources?.[0]);
      })
      .catch(() => undefined);
    // ask closes over the empty initial message list, which is what a fresh search needs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [incoming, me]);

  function submit(event: FormEvent) {
    event.preventDefault();
    void ask(prompt, true);
  }

  return (
    <div className="study-grid">
      <div className="study-col">
        <div className="scope-row">
          <select value={scopeType} onChange={(event) => setScopeType(event.target.value as 'library' | 'document')}>
            <option value="library">Whole library</option>
            <option value="document">One textbook</option>
          </select>
          {scopeType === 'document' && (
            <select value={documentId} onChange={(event) => setDocumentId(event.target.value)}>
              <option value="">Select…</option>
              {docs.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.title}
                </option>
              ))}
            </select>
          )}
        </div>

        <div className="thread">
          {messages.length === 0 && !busy && <p className="empty">Ask a question. Cited pages open in the textbook.</p>}
          {messages.map((message, index) => (
            <div key={index} className={`bubble bubble-${message.role}`}>
              <div className="bubble-label">{message.role === 'user' ? 'You' : 'Argus'}</div>
              {message.role === 'assistant' ? (
                <AnswerBlock
                  text={message.content}
                  sources={message.sources ?? []}
                  onOpenPage={(docId, page) => {
                    const match = (message.sources ?? []).find((source) => source.document_id === docId) ?? message.sources?.[0];
                    if (match) openPdf({ ...match, document_id: docId }, page);
                  }}
                />
              ) : (
                <p style={{ margin: 0 }}>{message.content}</p>
              )}
              {message.role === 'assistant' && (message.sources?.length ?? 0) > 0 && (
                <div className="sources-list" style={{ marginTop: '0.75rem' }}>
                  {message.sources!.map((source, sourceIndex) => (
                    <button
                      key={`${source.document_id}-${source.page_number}-${sourceIndex}`}
                      type="button"
                      className="source-item"
                      onClick={() => openPdf(source)}
                    >
                      <div className="source-item-title">
                        {source.document_title || 'Source'} · p{source.page_number}
                      </div>
                      <div className="source-excerpt">{source.text}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
          {busy && <p className="loading">Searching the textbooks…</p>}
          {error && <p className="upload-msg" style={{ color: 'var(--danger)' }}>{error}</p>}
        </div>

        <form className="composer" onSubmit={submit}>
          <textarea
            rows={3}
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="Ask a follow-up"
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                void ask(prompt, true);
              }
            }}
          />
          <div className="composer-actions">
            <span />
            <button type="submit" className="btn btn-primary" disabled={busy || !prompt.trim()}>
              {busy ? 'Working…' : 'Ask'}
            </button>
          </div>
        </form>
      </div>

      <div className="study-col">
        <div className="panel pdf-panel">
          <div className="section-label">{pdfTitle || 'Textbook'}</div>
          {pdfDocId ? (
            <PdfViewer documentId={pdfDocId} page={pdfPage} />
          ) : (
            <p className="empty">The cited page opens here.</p>
          )}
        </div>
      </div>
    </div>
  );
}
