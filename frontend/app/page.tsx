'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function Home() {
  const router = useRouter();
  const [sessionId] = useState(() => `session-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`);
  const [file, setFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFile(e.target.files?.[0] || null);
    setError(null);
  };

  const handleUpload = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!file) {
      setError('Please select a file');
      return;
    }

    setIsLoading(true);

    try {
      // For now, just proceed to query page
      // In Phase 8, we'll implement actual CSV upload to backend
      const uploadedFileName = file.name;

      router.push(`/query?session=${sessionId}&file=${encodeURIComponent(uploadedFileName)}`);
    } catch (err) {
      setError('Upload failed. Please try again.');
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-lg shadow-lg p-8">
          {/* Header */}
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">FP&A Copilot</h1>
            <p className="text-gray-600">Financial Planning & Analysis with AI</p>
          </div>

          {/* Upload Form */}
          <form onSubmit={handleUpload} className="space-y-6">
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-indigo-500 transition">
              <input
                type="file"
                accept=".csv,.xlsx"
                onChange={handleFileChange}
                className="hidden"
                id="file-input"
                disabled={isLoading}
              />
              <label htmlFor="file-input" className="cursor-pointer block">
                <div className="text-4xl mb-2">📊</div>
                <div className="text-sm text-gray-600">
                  {file ? (
                    <div>
                      <div className="font-semibold text-gray-900">{file.name}</div>
                      <div className="text-xs text-gray-500 mt-1">Click to change</div>
                    </div>
                  ) : (
                    <div>
                      <div className="font-semibold text-gray-900">Drop your CSV or Excel file</div>
                      <div className="text-xs text-gray-500 mt-1">or click to browse</div>
                    </div>
                  )}
                </div>
              </label>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={!file || isLoading}
              className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white font-semibold py-3 px-4 rounded-lg transition flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <div className="animate-spin">⏳</div>
                  Uploading...
                </>
              ) : (
                <>
                  <span>↗</span>
                  Start Q&A Session
                </>
              )}
            </button>
          </form>

          {/* Session Info */}
          <div className="mt-6 p-4 bg-gray-50 rounded-lg text-xs text-gray-600">
            <div className="font-mono break-all">
              Session: {sessionId.slice(0, 20)}...
            </div>
          </div>

          {/* Features */}
          <div className="mt-8 pt-6 border-t border-gray-200 space-y-3 text-sm text-gray-600">
            <div className="flex gap-2">
              <span>✓</span>
              <span>Ask questions about your financial data</span>
            </div>
            <div className="flex gap-2">
              <span>✓</span>
              <span>Get AI-powered analysis and insights</span>
            </div>
            <div className="flex gap-2">
              <span>✓</span>
              <span>View cost and performance metrics</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
