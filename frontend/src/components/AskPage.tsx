import { forwardRef, useState } from 'react';
import { askQuestion, type DrinkRef } from '../api';
import './AskPage.css';

const MOOD_CHIPS = [
  { label: 'floral', query: 'floral and clean' },
  { label: 'smoky', query: 'something smoky' },
  { label: 'low proof', query: 'low proof crowd pleaser' },
  { label: 'whisky', query: 'whisky forward' },
  { label: 'non alcoholic', query: 'good for non drinkers' },
];

const AskPage = forwardRef<HTMLElement>((_props, ref) => {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answer, setAnswer] = useState<string | null>(null);
  const [drink, setDrink] = useState<DrinkRef | null>(null);

  const ask = async (text: string) => {
    if (!text.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const response = await askQuestion(text);
      setAnswer(response.answer);
      setDrink(response.drink);
    } catch (err) {
      // RateLimitError and NetworkError both extend Error, and every message
      // from api.ts is already written for a reader.
      setError(err instanceof Error ? err.message : 'Something went wrong asking the bartender.');
      setAnswer(null);
      setDrink(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    ask(question);
  };

  return (
    <section className="page ask-page" ref={ref}>
      <div className="ask-wrap">
        <svg className="ask-mark doodle" viewBox="0 0 60 60" aria-hidden="true">
          <path d="M30 6 C42 6 52 15 52 27 C52 38 43 46 31 47 L28 54" />
          <circle className="doodle-fill doodle-fill--ink" cx="18" cy="14" r="1.6" />
          <circle className="doodle-fill doodle-fill--osmanthus" cx="46" cy="42" r="1.6" />
        </svg>

        <div>
          <h2 className="ask-title hand">
            Need recommendations? <span className="accent">Just ask.</span>
          </h2>
          <p className="ask-sub">Smoky, floral, boozy, easy for a crowd — tell me the mood.</p>
        </div>

        <form className="ask-form" onSubmit={handleSubmit}>
          <input
            className="ask-input"
            type="text"
            placeholder="Something smoky and low effort..."
            autoComplete="off"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={loading}
          />
          <button
            className="ask-submit"
            type="submit"
            aria-label="Ask"
            disabled={loading || !question.trim()}
          >
            <svg className="ask-submit__icon" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M5 12 L19 12 M13 6 L19 12 L13 18" />
            </svg>
          </button>
        </form>

        <div className="chips">
          {MOOD_CHIPS.map((chip) => (
            <button
              key={chip.label}
              className="chip"
              type="button"
              disabled={loading}
              onClick={() => {
                setQuestion(chip.query);
                ask(chip.query);
              }}
            >
              {chip.label}
            </button>
          ))}
        </div>

        {loading && <p className="ask-sub">Thinking it over...</p>}

        {error && <div className="answer-error">{error}</div>}

        {answer && !error && (
          <div className="answer">
            {drink && <span className="answer-name hand">{drink.name}</span>}
            <p className="answer-body">{answer}</p>
          </div>
        )}
      </div>
    </section>
  );
});

AskPage.displayName = 'AskPage';

export default AskPage;
