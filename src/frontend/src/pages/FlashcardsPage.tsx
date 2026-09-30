import { FormEvent, useState } from 'react';
import { broadcastFlashcards, chat, emailFlashcards, extractPages } from '../api';
import PdfViewer from '../components/PdfViewer';
import { useMe } from '../me';
import type { Source } from '../types';

type Card = {
  front: string;
  back: string;
  citations?: string[];
};

export default function FlashcardsPage() {
  const me = useMe();
  const [query, setQuery] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [cards, setCards] = useState<Card[]>([]);
  const [flipped, setFlipped] = useState<Set<number>>(new Set());
  const [sources, setSources] = useState<Source[]>([]);
  const [pdfDocId, setPdfDocId] = useState<string | null>(null);
  const [pdfPage, setPdfPage] = useState(1);

  function openPage(page: number) {
    const source = sources.find((item) => item.page_number === page) ?? sources[0];
    if (!source) return;
    setPdfDocId(source.document_id);
    setPdfPage(page);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const topic = query.trim();
    if (!topic || busy) return;
    setBusy(true);
    setError('');
    setNotice('');
    setFlipped(new Set());
    try {
      const response = await chat([{ role: 'user', content: topic }], 'flashcards', { type: 'library' });
      const raw = (response.structured?.items ?? []) as Card[];
      setCards(raw.filter((item) => item && item.front));
      setSources(response.sources ?? []);
      const first = response.sources?.[0];
      if (first) {
        setPdfDocId(first.document_id);
        setPdfPage(first.page_number);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Flashcards failed');
    } finally {
      setBusy(false);
    }
  }

  function toggle(index: number) {
    setFlipped((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  async function emailMe() {
    setNotice('');
    setError('');
    try {
      await emailFlashcards(query.trim() || 'Study topic', cards, sources);
      setNotice('Sent to your email.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Email failed');
    }
  }

  async function sendToSubscribers() {
    const documentId = sources[0]?.document_id;
    if (!documentId) {
      setError('These cards are not tied to a textbook yet.');
      return;
    }
    setNotice('');
    setError('');
    try {
      const result = await broadcastFlashcards(documentId, query.trim() || 'Study topic', cards, sources);
      setNotice(`Sent to ${result.sent} subscriber${result.sent === 1 ? '' : 's'}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Broadcast failed');
    }
  }

  return (
    <div className="study-grid">
      <div className="study-col">
        <form className="home-search home-search-inline" onSubmit={submit}>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Make flashcards about…"
            aria-label="Flashcard topic"
          />
          <button type="submit" className="btn btn-primary" disabled={busy || !query.trim()}>
            {busy ? 'Writing…' : 'Make cards'}
          </button>
        </form>
        {cards.length > 0 && (
          <div className="composer-actions">
            <button type="button" className="btn btn-ghost" onClick={() => void emailMe()}>
              Email me
            </button>
            {me?.is_admin && (
              <button type="button" className="btn btn-ghost" onClick={() => void sendToSubscribers()}>
                Send to subscribers
              </button>
            )}
          </div>
        )}
        {notice && <p className="upload-msg">{notice}</p>}
        {error && <p className="upload-msg" style={{ color: 'var(--danger)' }}>{error}</p>}
        {cards.map((card, index) => {
          const text = `${card.front} ${card.back} ${(card.citations ?? []).join(' ')}`;
          const pages = extractPages(text);
          const showBack = flipped.has(index);
          return (
            <button key={index} type="button" className="flashcard flashcard-flip" onClick={() => toggle(index)}>
              <div className="flashcard-front">{showBack ? card.back : card.front}</div>
              <div className="flashcard-hint">{showBack ? 'Front' : 'Click to flip'}</div>
              {pages.length > 0 && (
                <div>
                  {pages.map((page) => (
                    <span
                      key={page}
                      role="link"
                      className="cite-chip"
                      onClick={(event) => {
                        event.stopPropagation();
                        openPage(page);
                      }}
                    >
                      p{page}
                    </span>
                  ))}
                </div>
              )}
            </button>
          );
        })}
      </div>
      <div className="study-col">
        <div className="panel pdf-panel">
          <div className="section-label">Textbook</div>
          {pdfDocId ? <PdfViewer documentId={pdfDocId} page={pdfPage} /> : <p className="empty">Citations open the page here.</p>}
        </div>
      </div>
    </div>
  );
}
