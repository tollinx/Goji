const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface AskResponse {
  answer: string;
  citations: any[];
}

export interface ErrorResponse {
  error: string;
}

export class RateLimitError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'RateLimitError';
  }
}

export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NetworkError';
  }
}

export async function askQuestion(question: string): Promise<AskResponse> {
  try {
    const response = await fetch(`${API_URL}/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question }),
    });

    if (response.status === 429) {
      const data: ErrorResponse = await response.json();
      throw new RateLimitError(data.error || 'Rate limit exceeded. Please try again later.');
    }

    if (!response.ok) {
      const data: ErrorResponse = await response.json().catch(() => ({ error: 'An error occurred' }));
      throw new Error(data.error || `Server error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof RateLimitError) {
      throw error;
    }
    if (error instanceof TypeError) {
      throw new NetworkError('Could not connect to backend. Please check your connection.');
    }
    throw error;
  }
}
