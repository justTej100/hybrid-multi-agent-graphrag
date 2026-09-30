import { FormEvent, useState } from 'react';
import { chat, extractPages } from '../api';
import PdfViewer from '../components/PdfViewer';
import type { Source } from '../types';

type QuizQuestion = {
  question: string;
  choices: string[];
  correct_choice: number;
};

export default function QuizPage() {
  const [query, setQuery] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [picks, setPicks] = useState<Record<number, number>>({});
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
    setPicks({});
    try {
      const response = await chat(
        [{ role: 'user', content: topic }],
        'quiz',
        { type: 'library' },
      );
      const raw = (response.structured?.questions ?? []) as QuizQuestion[];
      setQuestions(raw.filter((item) => item && item.question && Array.isArray(item.choices)));
      setSources(response.sources ?? []);
      const first = response.sources?.[0];
      if (first) {
        setPdfDocId(first.document_id);
        setPdfPage(first.page_number);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Quiz failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="study-grid">
      <div className="study-col">
        <form className="home-search home-search-inline" onSubmit={submit}>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Quiz me on…"
            aria-label="Quiz topic"
          />
          <button type="submit" className="btn btn-primary" disabled={busy || !query.trim()}>
            {busy ? 'Writing…' : 'Quiz'}
          </button>
        </form>
        {error && <p className="upload-msg" style={{ color: 'var(--danger)' }}>{error}</p>}
        {questions.map((item, index) => {
          const picked = picks[index];
          const pages = extractPages(`${item.question} ${item.choices.join(' ')}`);
          return (
            <div key={index} className="panel quiz-card">
              <p className="quiz-question">{item.question}</p>
              <div className="quiz-choices">
                {item.choices.map((choice, choiceIndex) => {
                  const revealed = picked !== undefined;
                  const correct = choiceIndex === item.correct_choice;
                  const cls = revealed
                    ? correct
                      ? 'choice choice-correct'
                      : choiceIndex === picked
                        ? 'choice choice-wrong'
                        : 'choice'
                    : 'choice';
                  return (
                    <button
                      key={choiceIndex}
                      type="button"
                      className={cls}
                      disabled={revealed}
                      onClick={() => setPicks((prev) => ({ ...prev, [index]: choiceIndex }))}
                    >
                      {choice}
                    </button>
                  );
                })}
              </div>
              {pages.length > 0 && (
                <div>
                  {pages.map((page) => (
                    <button key={page} type="button" className="cite-chip" onClick={() => openPage(page)}>
                      p{page}
                    </button>
                  ))}
                </div>
              )}
            </div>
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
