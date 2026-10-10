import { useState, useEffect, useRef } from "react";
import { api } from "../api/client";

interface Doc {
  name: string;
}

export default function Documents() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [uploading, setUploading] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [message, setMessage] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocs = async () => {
    try {
      const res = await api.get("/documents");
      setDocs(res.data.documents);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setUploading(true);
    setMessage("");
    const form = new FormData();
    Array.from(files).forEach((f) => form.append("files", f));
    try {
      const res = await api.post("/documents/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setMessage(`Added: ${res.data.added} | Skipped: ${res.data.skipped}`);
      await fetchDocs();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Upload failed";
      setMessage(msg);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleClear = async () => {
    if (!confirm("Remove all documents? This cannot be undone.")) return;
    setClearing(true);
    setMessage("");
    try {
      await api.delete("/documents");
      setMessage("All documents removed");
      setDocs([]);
    } catch {
      setMessage("Failed to clear documents");
    } finally {
      setClearing(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <h1 className="text-xl font-semibold mb-6">Documents</h1>

      {/* Upload */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
        <h2 className="text-sm font-medium text-gray-300 mb-3">Upload PDFs or Markdown files</h2>
        <p className="text-xs text-gray-500 mb-4">
          Existing documents with the same name are skipped. Use Clear All before re-indexing a document.
        </p>
        <label className="flex items-center justify-center border-2 border-dashed border-gray-700 rounded-lg h-28 cursor-pointer hover:border-indigo-500 transition-colors">
          <div className="text-center">
            <p className="text-sm text-gray-400">Click to select files</p>
            <p className="text-xs text-gray-600 mt-1">.pdf, .md</p>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.md"
            className="hidden"
            onChange={handleUpload}
          />
        </label>
        {uploading && (
          <p className="text-sm text-indigo-400 mt-3 animate-pulse">Processing files...</p>
        )}
      </div>

      {/* Status message */}
      {message && (
        <p className="text-sm text-gray-300 mb-4">{message}</p>
      )}

      {/* Document list */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-gray-300">
            Knowledge base{" "}
            <span className="text-gray-600">({docs.length} docs)</span>
          </h2>
          <button
            onClick={fetchDocs}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            Refresh
          </button>
        </div>

        {docs.length === 0 ? (
          <p className="text-sm text-gray-600">No documents yet</p>
        ) : (
          <ul className="space-y-2">
            {docs.map((doc) => (
              <li
                key={doc.name}
                className="flex items-center gap-2 text-sm text-gray-300"
              >
                <span className="w-2 h-2 rounded-full bg-indigo-500 flex-shrink-0" />
                {doc.name}
              </li>
            ))}
          </ul>
        )}

        {docs.length > 0 && (
          <button
            onClick={handleClear}
            disabled={clearing}
            className="mt-5 text-sm text-red-400 hover:text-red-300 disabled:opacity-50 transition-colors"
          >
            {clearing ? "Clearing..." : "Clear all documents"}
          </button>
        )}
      </div>
    </div>
  );
}
