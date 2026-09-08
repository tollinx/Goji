/**
 * Client for the Goji & Gin API.
 *
 * Every error response from the backend is `{ "detail": string }`, so callers
 * can rely on a single shape.
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface DrinkRef {
  id: string;
  name: string;
}

export interface AskResponse {
  answer: string;
  drink: DrinkRef | null;
}

/** Thrown on 429 so the UI can distinguish "slow down" from a real failure. */
export class RateLimitError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'RateLimitError';
  }
}

/** Thrown when the backend can't be reached at all. */
export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NetworkError';
  }
}

async function detailOf(response: Response, fallback: string): Promise<string> {
  const body = await response.json().catch(() => null);
  // Our own errors send a string. FastAPI's built-in validation errors send an
  // array of field objects, which is not something to show a person.
  return typeof body?.detail === 'string' ? body.detail : fallback;
}

export async function askQuestion(question: string): Promise<AskResponse> {
  let response: Response;

  try {
    response = await fetch(`${API_URL}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
  } catch {
    // fetch only rejects when the request never completed.
    throw new NetworkError('Could not reach the backend. Is it running?');
  }

  if (response.status === 429) {
    throw new RateLimitError(await detailOf(response, 'Too many requests. Try again shortly.'));
  }

  if (!response.ok) {
    throw new Error(await detailOf(response, `Server error: ${response.status}`));
  }

  return response.json();
}
