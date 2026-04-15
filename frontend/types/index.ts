export type PaperStatus = 'pending' | 'processing' | 'done' | 'failed';

export interface FieldValue {
  value: string | number | null;
  unit: string | null;
  evidence: string | null;
  page: number | null;
  confidence: number;
}

export interface Extraction {
  title: string | null;
  authors: string[];
  journal: string | null;
  year: number | null;
  doi: string | null;
  abstract: string | null;
  impact_factor: number | null;
  material_info: Record<string, FieldValue>;
  input_variables: Record<string, FieldValue>;
  output_variables: Record<string, FieldValue>;
  raw_summary: string;
  custom_fields: Record<string, FieldValue>;
}

export interface Paper {
  id: string;
  file_name: string;
  file_path: string;
  status: PaperStatus;
  title: string | null;
  journal: string | null;
  year: number | null;
  authors: string[];
  impact_factor: number | null;
  processed_at: string | null;
  created_at: string;
  error_message: string | null;
  has_extraction: boolean;
  // full detail only
  sha256?: string;
  file_size_bytes?: number | null;
  doi?: string | null;
  abstract?: string | null;
  extraction?: Extraction | null;
  summary_path?: string | null;
}

export interface PaperList {
  items: Paper[];
  total: number;
  skip: number;
  limit: number;
}

export interface ScanResult {
  total_found: number;
  new_processed: number;
  skipped: number;
  failed: number;
  errors: string[];
  duration_seconds: number;
}

export interface AppSettings {
  paper_folder: string;
  folder_status: 'not_set' | 'ok' | 'not_found';
  pdf_count: number;
  custom_parameters: string; // JSON string
}

export interface LlmInfo {
  provider: string;
  model: string;
  max_tokens: number;
  temperature: number;
  timeout_seconds: number;
}
