'use client';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface QueryRequest {
  query: string;
  session_id?: string;
}

export interface QueryResponse {
  query: string;
  answer: string;
  refusal_reason?: string;
  guardrails_status: Record<string, any>;
  traces: Record<string, any>;
}

export async function queryAPI(req: QueryRequest): Promise<QueryResponse> {
  const response = await fetch(`${API_URL}/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(req),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail?.reason || error.detail || 'Query failed');
  }

  return response.json();
}

export async function getStatus(): Promise<Record<string, any>> {
  const response = await fetch(`${API_URL}/status`);
  if (!response.ok) {
    throw new Error('Failed to get status');
  }
  return response.json();
}

export async function getGuardrailsStatus(sessionId: string): Promise<Record<string, any>> {
  const response = await fetch(`${API_URL}/guardrails/${sessionId}`);
  if (!response.ok) {
    throw new Error('Failed to get guardrails status');
  }
  return response.json();
}
