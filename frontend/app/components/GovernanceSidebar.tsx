'use client';

interface TraceStep {
  agent: string;
  model: string;
  duration_ms: number;
  input_tokens: number;
  output_tokens: number;
  cost: number;
}

interface GuardrailsStatus {
  rate_limit: {
    remaining_requests: number;
    max_per_minute: number;
  };
  query_cap: {
    used_queries: number;
    max_per_session: number;
    remaining: number;
  };
  cost_ceiling: {
    spent_today: number;
    max_daily: number;
    remaining: number;
  };
}

interface GovernanceSidebarProps {
  traces?: Record<string, TraceStep>;
  guardrails?: GuardrailsStatus;
  confidenceScore?: number;
}

export function GovernanceSidebar({
  traces,
  guardrails,
  confidenceScore = 0.7,
}: GovernanceSidebarProps) {
  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'bg-green-100 border-green-300 text-green-900';
    if (score >= 0.6) return 'bg-yellow-100 border-yellow-300 text-yellow-900';
    return 'bg-red-100 border-red-300 text-red-900';
  };

  return (
    <div className="w-80 bg-gray-50 border-l border-gray-200 p-6 overflow-y-auto">
      <h2 className="text-lg font-semibold text-gray-900 mb-6">Governance</h2>

      {/* Confidence Score */}
      <div className="mb-6">
        <h3 className="text-sm font-medium text-gray-700 mb-2">Confidence</h3>
        <div className={`border rounded-lg p-3 ${getConfidenceColor(confidenceScore)}`}>
          <div className="text-2xl font-bold">{(confidenceScore * 100).toFixed(0)}%</div>
          <div className="text-xs mt-1">
            {confidenceScore >= 0.8 ? '✓ High confidence' : confidenceScore >= 0.6 ? '⚠ Medium confidence' : '✗ Low confidence'}
          </div>
        </div>
      </div>

      {/* Agent Traces */}
      {traces && Object.keys(traces).length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Agent Steps</h3>
          <div className="space-y-3">
            {Object.entries(traces).map(([key, step]) => (
              <div key={key} className="bg-white border border-gray-200 rounded-lg p-3 text-xs">
                <div className="font-semibold text-gray-900 mb-2 capitalize">{step.agent}</div>
                <div className="space-y-1 text-gray-600">
                  <div>Model: <span className="text-gray-900">{step.model.split('-').slice(1).join('-')}</span></div>
                  <div>Time: <span className="text-gray-900">{step.duration_ms}ms</span></div>
                  <div>Tokens: <span className="text-gray-900">{step.input_tokens} in, {step.output_tokens} out</span></div>
                  <div>Cost: <span className="text-gray-900">${step.cost.toFixed(4)}</span></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Guardrails Status */}
      {guardrails && (
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Rate Limits</h3>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-600">Requests/min:</span>
              <span className="font-semibold text-gray-900">
                {guardrails.rate_limit.remaining_requests}/{guardrails.rate_limit.max_per_minute}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Queries/session:</span>
              <span className="font-semibold text-gray-900">
                {guardrails.query_cap.remaining}/{guardrails.query_cap.max_per_session}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Daily budget:</span>
              <span className="font-semibold text-gray-900">
                ${guardrails.cost_ceiling.remaining.toFixed(2)}/${guardrails.cost_ceiling.max_daily.toFixed(2)}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-gray-200 text-xs text-gray-500">
        <p>All responses are logged for audit.</p>
      </div>
    </div>
  );
}
