import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { useAuth } from "../context/AuthContext";
import { DOCUMENT_TYPE_OPTIONS, formatDocumentType, formatFileSize } from "../shared/documents";
import { documentsApi } from "../shared/services";
import type { DocumentType } from "../types";

export function EmployeeDocumentsPage() {
  const { organization, token, user } = useAuth();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const orgId = organization?.id ?? "";
  const employeeId = user?.id ?? "";

  const [documentType, setDocumentType] = useState<DocumentType>("TRAINING_CERTIFICATE");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const documentsQuery = useQuery({
    queryKey: ["documents", orgId, employeeId],
    queryFn: () => documentsApi.listForEmployee(orgId, employeeId, token!),
    enabled: Boolean(orgId && token && employeeId),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      documentsApi.uploadDocument(orgId, token!, employeeId, documentType, file),
    onSuccess: () => {
      setSuccess("Document uploaded successfully.");
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["documents", orgId, employeeId] });
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    onError: (err: Error) => {
      setSuccess(null);
      setError(err.message);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (documentId: string) => documentsApi.delete(orgId, documentId, token!),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents", orgId, employeeId] });
    },
  });

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(null);
    setSuccess(null);
    uploadMutation.mutate(file);
  };

  const handleViewDocument = async (documentId: string) => {
    if (!token) return;
    try {
      const result = await documentsApi.getDownloadUrl(orgId, documentId, token);
      window.open(result.download_url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open document");
    }
  };

  return (
    <div className="space-y-6" data-testid="employee-documents-page">
      <div>
        <h1 className="text-2xl font-semibold">My documents</h1>
        <p className="text-sm text-slate-500">
          Upload training certificates and employment documents to S3-backed storage.
        </p>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-medium">Upload document</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="font-medium text-slate-700">Document type</span>
            <select
              value={documentType}
              onChange={(event) => setDocumentType(event.target.value as DocumentType)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            >
              {DOCUMENT_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span className="font-medium text-slate-700">File (PDF, JPEG, PNG — max 5MB)</span>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
              onChange={handleFileChange}
              disabled={uploadMutation.isPending}
              className="mt-1 w-full text-sm"
              data-testid="employee-document-file-input"
            />
          </label>
        </div>
        {uploadMutation.isPending && (
          <p className="mt-3 text-sm text-slate-600">Uploading to S3...</p>
        )}
        {error && (
          <p className="mt-3 text-sm text-red-600" role="alert">
            {error}
          </p>
        )}
        {success && (
          <p className="mt-3 text-sm text-green-700" data-testid="document-upload-success">
            {success}
          </p>
        )}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-medium">Uploaded documents</h2>
        {documentsQuery.isLoading && <p className="mt-3 text-slate-600">Loading...</p>}
        {documentsQuery.data?.length === 0 && (
          <p className="mt-3 text-sm text-slate-500" data-testid="employee-documents-empty">
            No documents uploaded yet.
          </p>
        )}
        {documentsQuery.data && documentsQuery.data.length > 0 && (
          <ul className="mt-4 space-y-3">
            {documentsQuery.data.map((document) => (
              <li
                key={document.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-100 px-4 py-3"
                data-testid="employee-document-card"
              >
                <div>
                  <p className="font-medium">{document.file_name}</p>
                  <p className="text-sm text-slate-600">{formatDocumentType(document.document_type)}</p>
                  <p className="text-sm text-slate-500">{formatFileSize(document.size_bytes)}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => void handleViewDocument(document.id)}
                    className="rounded-md border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50"
                    data-testid="employee-document-view"
                  >
                    View
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteMutation.mutate(document.id)}
                    disabled={deleteMutation.isPending}
                    className="rounded-md border border-red-200 px-3 py-1.5 text-sm text-red-700 hover:bg-red-50"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
