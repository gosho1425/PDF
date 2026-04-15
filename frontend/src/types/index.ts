/**
 * TypeScript types mirroring the backend Pydantic schemas.
 * Keep these in sync with backend/app/schemas/
 */

export type PaperStatus =
  | 'uploaded'
  | 'parsing'
  | 'parsed'
  | 'extracting'
  | 'extracted'
  | 'review_needed'
  | 'failed';

export type ExtractionStatus =
  | 'pending'
  | 'complete'
  | 'partial'
  | 'failed'
  | 'needs_review';

export interface PaperListItem {
  id: string;
  original_filename: string;
  title: string | null;
  doi: string | null;
  publication_year: number | null;
  status: PaperStatus;
  page_count: number | null;
  file_size_bytes: number | null;
  created_at: string;
  updated_at: string;
  journal_name: string | null;
  author_names: string[];
  has_extraction: boolean;
  needs_review: boolean;
}

export interface PaperDetail {
  id: string;
  original_filename: string;
  file_size_bytes: number | null;
  file_hash_sha256: string | null;
  page_count: number | null;
  status: PaperStatus;
  parse_error: string | null;
  extraction_error: string | null;
  title: string | null;
  doi: string | null;
  abstract: string | null;
  publication_year: number | null;
  keywords: string[] | null;
  volume: string | null;
  issue: string | null;
  pages: string | null;
  journal: { id: string; name: string } | null;
  authors: { name: string; position: number }[];
  parse_method: string | null;
  schema_version: string | null;
  summary_available: boolean;
  extraction_available: boolean;
  created_at: string;
  updated_at: string;
}

export interface SourceEvidence {
  id: string;
  field_name: string;
  field_value: string | null;
  source_text: string | null;
  page_numbers: number[] | null;
  section: string | null;
  confidence: number | null;
  is_inferred: boolean;
  inference_reasoning: string | null;
}

export interface MaterialEntity {
  id: string;
  name: string | null;
  composition: string | null;
  stoichiometry: string | null;
  dopants: string[] | null;
  substrate: string | null;
  layer_stack: string | null;
  device_structure: string | null;
  crystal_structure: string | null;
  phase: string | null;
  dimensionality: string | null;
  morphology: string | null;
}

export interface ProcessCondition {
  id: string;
  parameter_name: string;
  value_numeric: number | null;
  value_text: string | null;
  unit: string | null;
  variable_role: 'input' | 'output' | 'contextual';
  confidence: number | null;
  is_inferred: boolean;
  notes: string | null;
}

export interface MeasurementMethod {
  id: string;
  technique_name: string;
  category: string | null;
  description: string | null;
}

export interface ResultProperty {
  id: string;
  property_name: string;
  value_numeric: number | null;
  value_min: number | null;
  value_max: number | null;
  value_text: string | null;
  unit: string | null;
  conditions: string | null;
  variable_role: 'input' | 'output' | 'contextual';
  confidence: number | null;
  is_inferred: boolean;
  needs_review: boolean;
}

export interface ExtractionRecord {
  id: string;
  paper_id: string;
  schema_version: string;
  llm_model: string | null;
  is_canonical: boolean;
  status: ExtractionStatus;
  summary_text: string | null;
  main_findings: string | null;
  claimed_mechanism: string | null;
  limitations: string | null;
  notable_novelty: string | null;
  relevant_for_optimization: boolean | null;
  bibliographic_info: Record<string, unknown> | null;
  journal_quality: Record<string, unknown> | null;
  input_variables: Record<string, unknown> | null;
  output_variables: Record<string, unknown> | null;
  contextual_notes: Record<string, unknown> | null;
  human_edited: boolean;
  reviewed_by: string | null;
  review_notes: string | null;
  created_at: string;
  updated_at: string;
  materials: MaterialEntity[];
  process_conditions: ProcessCondition[];
  measurement_methods: MeasurementMethod[];
  result_properties: ResultProperty[];
}

export interface PaperListResponse {
  items: PaperListItem[];
  total: number;
  skip: number;
  limit: number;
}

/** Result returned by POST /papers/scan */
export interface ScanResult {
  task_id: string;
  status: string;
  ingest_dir: string;
  message: string;
}

/** Result returned by GET /papers/ingest-status */
export interface IngestStatus {
  ingest_dir: string;
  mounted: boolean;
  pdf_count_in_folder: number | null;
  hint: string | null;
}

/** Result returned by GET /jobs/{taskId}/celery-status after a scan */
export interface ScanSummary {
  folder: string;
  found: number;
  skipped_duplicates: number;
  ingested: number;
  failed: number;
  errors: string[];
  task_ids: string[];
}

export interface ExportRequest {
  paper_ids?: string[] | null;
  format: 'csv' | 'json';
  include_raw_extraction: boolean;
  include_source_evidence: boolean;
}
