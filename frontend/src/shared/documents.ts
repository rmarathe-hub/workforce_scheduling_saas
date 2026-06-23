import type { DocumentType } from "../types";

export const DOCUMENT_TYPE_OPTIONS: { value: DocumentType; label: string }[] = [
  { value: "TRAINING_CERTIFICATE", label: "Training certificate" },
  { value: "FOOD_SAFETY_CERTIFICATE", label: "Food safety certificate" },
  { value: "CPR_CERTIFICATE", label: "CPR certificate" },
  { value: "SIGNED_EMPLOYMENT_FORM", label: "Signed employment form" },
  { value: "ID_WORK_AUTHORIZATION", label: "ID / work authorization" },
];

export function formatDocumentType(type: DocumentType): string {
  return DOCUMENT_TYPE_OPTIONS.find((option) => option.value === type)?.label ?? type;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
