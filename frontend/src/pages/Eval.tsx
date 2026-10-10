import { useState } from "react";

interface EvalScores {
  faithfulness: number;
  answer_relevancy: number;
  context_precision: number;
  context_recall: number;
}

interface EvalDetail {
  question: string;
  answer: string;
  source: string;
}

const METRIC_LABELS: Record<keyof EvalScores, string> = {
  faithfulness: "Faithfulness",
  answer_relevancy: "Answer Relevancy",
  context_precision: "Context Precision",
  context_recall: "Context Recall",
};

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 80 ? "bg-green-500" : pct >= 60 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-300">{label}</span>
        <span className="text-gray-400">{pct}%</span>
      </div>
      <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function Eval() {
  const [running, setRunning] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [scores, setScores] = useState<EvalScores | null>(null);
  const [details, setDetails] = useState<EvalDetail[]>([]);
  const [error, setError] = useState("");
  const token = localStorage.getItem("token");

  const runEval = async () => {
    setRunning(true);
    setLogs([]);
    setScores(null);
    setDetails([]);
    setError("");

    try {
      const response = await fetch("http://localhost:8000/eval/run", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;
          try {
            const event = JSON.parse(raw);
            if (event.type === "progress") {
              setLogs((prev) => [...prev, event.message]);
            } else if (event.type === "result") {
              setScores(event.scores);
              setDetails(event.details);
            } else if (event.type === "error") {
              setError(event.message);
            }
          } catch {
            // skip
          }
        }
      }
    } catch {
      setError("Connection error. Is the server running?");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Evaluation</h1>
        <button
          onClick={runEval}
          disabled={running}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
        >
          {running ? "Running..." : "Run Evaluation"}
        </button>
      </div>

      <p className="text-sm text-gray-500 mb-6">
        Automatically generates questions from your documents and scores the RAG
        system using RAGAS metrics — faithfulness, answer relevancy, context
        precision, and context recall.
      </p>

      {/* Progress log */}
      {logs.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-6">
          <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">
            Progress
          </h2>
          <ul className="space-y-1">
            {logs.map((log, i) => (
              <li key={i} className="text-sm text-gray-400 flex gap-2 items-start">
                <span className="text-green-500 mt-0.5">✓</span>
                {log}
              </li>
            ))}
            {running && (
              <li className="text-sm text-indigo-400 animate-pulse">Working...</li>
            )}
          </ul>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-900/30 border border-red-800 rounded-xl p-4 mb-6 text-sm text-red-300">
          {error}
        </div>
      )}

      {/* Scores */}
      {scores && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
          <h2 className="text-sm font-medium text-gray-300 mb-4">Scores</h2>
          <div className="space-y-4">
            {(Object.keys(METRIC_LABELS) as (keyof EvalScores)[]).map((key) => (
              <ScoreBar key={key} label={METRIC_LABELS[key]} value={scores[key]} />
            ))}
          </div>
        </div>
      )}

      {/* Per-question details */}
      {details.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-sm font-medium text-gray-300 mb-4">
            Questions ({details.length})
          </h2>
          <div className="space-y-4">
            {details.map((d, i) => (
              <div key={i} className="border-t border-gray-800 pt-4 first:border-0 first:pt-0">
                <p className="text-xs text-gray-500 mb-1">
                  Source: {d.source}
                </p>
                <p className="text-sm font-medium text-gray-200 mb-2">
                  Q: {d.question}
                </p>
                <p className="text-sm text-gray-400">A: {d.answer}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
