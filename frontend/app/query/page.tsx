'use client';

import { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { queryAPI, QueryResponse } from '@/app/lib/api';
import { GovernanceSidebar } from '@/app/components/GovernanceSidebar';

interface Message {
  type: 'user' | 'assistant';
  content: string;
  response?: QueryResponse;
}

export default function QueryPage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get('session') || `session-${Date.now()}`;
  const fileName = searchParams.get('file') || 'data.csv';

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedMessage, setSelectedMessage] = useState<Message | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!input.trim()) {
      return;
    }

    const userMessage = input.trim();
    setInput('');
    setError(null);
    setIsLoading(true);

    // Add user message immediately
    setMessages((prev) => [...prev, { type: 'user', content: userMessage }]);

    try {
      // Query backend
      const response = await queryAPI({
        query: userMessage,
        session_id: sessionId,
      });

      // Add assistant response
      const assistantMessage: Message = {
        type: 'assistant',
        content: response.refusal_reason || response.answer,
        response,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setSelectedMessage(assistantMessage);
    } catch (err) {
      setError((err as Error).message);
      // Add error message
      setMessages((prev) => [
        ...prev,
        {
          type: 'assistant',
          content: `Error: ${(err as Error).message}`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const selectedResponse = selectedMessage?.response;

  return (
    <div className="flex h-screen bg-white">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b border-gray-200 bg-white p-4 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-gray-900">FP&A Copilot</h1>
            <p className="text-xs text-gray-500">Session: {sessionId.slice(0, 16)}... | File: {fileName}</p>
          </div>
          <Link
            href="/"
            className="text-sm px-3 py-2 text-gray-600 hover:bg-gray-100 rounded transition"
          >
            ← New Session
          </Link>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="h-full flex items-center justify-center text-center">
              <div>
                <div className="text-4xl mb-4">💬</div>
                <h2 className="text-xl font-semibold text-gray-900 mb-2">Ask about your financial data</h2>
                <p className="text-gray-600 max-w-sm">
                  Ask questions about budget variances, cost centers, spending trends, or get AI-powered financial analysis.
                </p>
              </div>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
              onClick={() => msg.response && setSelectedMessage(msg)}
            >
              <div
                className={`max-w-md px-4 py-3 rounded-lg ${
                  msg.type === 'user'
                    ? 'bg-indigo-600 text-white rounded-br-none'
                    : 'bg-gray-100 text-gray-900 rounded-bl-none cursor-pointer hover:bg-gray-200'
                }`}
              >
                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 text-gray-900 px-4 py-3 rounded-lg rounded-bl-none animate-pulse">
                <p className="text-sm">Analyzing your question...</p>
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 bg-white p-4">
          <form onSubmit={handleSubmit} className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about your data..."
              disabled={isLoading}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-50"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white font-semibold rounded-lg transition"
            >
              Send
            </button>
          </form>
        </div>
      </div>

      {/* Governance Sidebar */}
      <GovernanceSidebar
        traces={selectedResponse?.traces}
        guardrails={selectedResponse?.guardrails_status}
        confidenceScore={
          selectedResponse
            ? selectedResponse.refusal_reason
              ? 0.5
              : 0.8
            : undefined
        }
      />
    </div>
  );
}
