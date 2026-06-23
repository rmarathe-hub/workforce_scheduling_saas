import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { useAuth } from "../context/AuthContext";
import { DOCUMENT_TYPE_OPTIONS, formatDocumentType, formatFileSize } from "../shared/documents";
import { documentsApi, resourceApi } from "../shared/services";
import type { DocumentType } from "../types";

export function ManagerEmployeeDocumentsPage() {
  const { organization, token } = useAuth();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const orgId = organization?.id ?? "";

  const [employeeId, setEmployeeId] = useState("");
  const [documentType, setDocumentType] = useState<DocumentType>("TRAINING_CERTIFICATE");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const employeesQuery = useQuery({
    queryKey: ["employees", orgId],
    queryFn: () => resourceApi.employees(orgId, token!),
    enabled: Boolean(orgId && token),
  });

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

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !employeeId) return;
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
    <div className="space-y-6" data-testid="manager-employee-documents-page">
      <div>
        <h1 className="text-2xl font-semibold">Employee documents</h1>
        <p className="text-sm text-slate-500">View and upload documents for employees in your org.</p>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <label className="block text-sm font-medium text-slate-700" htmlFor="employee-select">
          Employee
        </label>
        <select
          id="employee-select"
          value={employeeId}
          onChange={(event) => setEmployeeId(event.target.value)}
          className="mt-1 w-full max-w-md rounded-md border border-slate-300 px-3 py-2"
          data-testid="manager-employee-select"
        >
          <option value="">Select an employee</option>
          {employeesQuery.data?.map((employee) => (
            <option key={employee.user_id} value={employee.user_id}>
              {employee.full_name} ({employee.email})
            </option>
          ))}
        </select>
      </section>

      {employeeId && (
        <>
          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-medium">Upload for selected employee</h2>
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
                <span className="font-medium text-slate-700">File</span>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
                  onChange={handleFileChange}
                  disabled={uploadMutation.isPending}
                  className="mt-1 w-full text-sm"
                />
              </label>
            </div>
            {uploadMutation.isPending && (
              <p className="mt-3 text-sm text-slate-600">Uploading to S3...</p>
            )}
            {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
            {success && <p className="mt-3 text-sm text-green-700">{success}</p>}
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-medium">Documents on file</h2>
            {documentsQuery.isLoading && <p className="mt-3 text-slate-600">Loading...</p>}
            {documentsQuery.data?.length === 0 && (
              <p className="mt-3 text-sm text-slate-500">No documents for this employee.</p>
            )}
            {documentsQuery.data && documentsQuery.data.length > 0 && (
              <ul className="mt-4 space-y-3">
                {documentsQuery.data.map((document) => (
                  <li
                    key={document.id}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-100 px-4 py-3"
                    data-testid="manager-employee-document-card"
                  >
                    <div>
                      <p className="font-medium">{document.file_name}</p>
                      <p className="text-sm text-slate-600">{formatDocumentType(document.document_type)}</p>
                      <p className="text-sm text-slate-500">
                        {formatFileSize(document.size_bytes)} · uploaded by{" "}
                        {document.uploaded_by_name ?? "Unknown"}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => void handleViewDocument(document.id)}
                      className="rounded-md border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50"
                    >
                      View
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
