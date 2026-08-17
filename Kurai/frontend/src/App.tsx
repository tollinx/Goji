import { useState } from 'react';
import { askQuestion, RateLimitError, NetworkError } from './api';
import './App.css';

const EXAMPLE_QUESTIONS = [
  "What does AC-2 require?",
  "How does CMMC Level 2 handle access control?",
  "What are the password requirements in NIST 800-53?",
  "Explain the difference between AC-2 and AC-3"
];

function App() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState<string | null>(null);
  const [citations, setCitations] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAsk = async (questionText: string) => {
    if (!questionText.trim()) return;

    setLoading(true);
    setError(null);
    setAnswer(null);
    setCitations([]);

    try {
      const response = await askQuestion(questionText);
      setAnswer(response.answer);
      setCitations(response.citations);
    } catch (err) {
      if (err instanceof RateLimitError) {
        setError(err.message);
      } else if (err instanceof NetworkError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleChipClick = (exampleQuestion: string) => {
    setQuestion(exampleQuestion);
    handleAsk(exampleQuestion);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleAsk(question);
  };

  return (
    <div className="app">
      <header className="header">
        <h1>Kurai — Compliance RAG Assistant</h1>
        <p className="subtitle">Ask questions about NIST 800-53, CMMC, and other compliance frameworks</p>
      </header>

      <main className="main">
        <div className="example-chips">
          <p className="chips-label">Try these examples:</p>
          <div className="chips-container">
            {EXAMPLE_QUESTIONS.map((q, idx) => (
              <button
                key={idx}
                className="chip"
                onClick={() => handleChipClick(q)}
                disabled={loading}
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="question-form">
          <textarea
            className="question-input"
            placeholder="Ask a compliance question..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={3}
            disabled={loading}
          />
          <button
            type="submit"
            className="submit-button"
            disabled={loading || !question.trim()}
          >
            {loading ? 'Asking...' : 'Ask'}
          </button>
        </form>

        {loading && (
          <div className="loading">
            <div className="spinner"></div>
            <p>Thinking...</p>
          </div>
        )}

        {error && (
          <div className="error">
            <strong>Error:</strong> {error}
          </div>
        )}

        {answer && (
          <div className="answer-container">
            <h2>Answer</h2>
            <p className="answer">{answer}</p>
            {citations.length > 0 && (
              <div className="citations">
                <h3>Citations</h3>
                <ul>
                  {citations.map((citation, idx) => (
                    <li key={idx}>{JSON.stringify(citation)}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
