import { FormEvent, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listDocuments } from '../api';

export default function HomePage() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [readyCount, setReadyCount] = useState<number | null>(null);

  useEffect(() => {
    listDocuments()
      .then((docs) => setReadyCount(docs.filter((doc) => doc.status === 'ready').length))
      .catch(() => setReadyCount(0));
  }, []);

  function submit(event: FormEvent) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    navigate(`/study?q=${encodeURIComponent(trimmed)}`);
  }

  const readyLine =
    readyCount === null
      ? 'Checking textbooks…'
      : readyCount === 1
        ? '1 textbook ready'
        : `${readyCount} textbooks ready`;

  return (
    <div className="home">
      <h1 className="home-title">Ask your textbooks</h1>
      <p className="home-ready">{readyLine}</p>
      <form className="home-search" onSubmit={submit}>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="What do you want to know?"
          aria-label="Question"
          autoFocus
        />
        <button type="submit" className="btn btn-primary" disabled={!query.trim()}>
          Search
        </button>
      </form>
    </div>
  );
}
