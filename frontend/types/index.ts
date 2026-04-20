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

// ── Phase 2: Optimization types ───────────────────────────────────────────────

export type VariableRole = 'input' | 'output' | 'material';
export type VariableType = 'continuous' | 'categorical' | 'integer' | 'boolean';
export type ExperimentStatus = 'planned' | 'running' | 'completed' | 'failed';
export type SourceType = 'literature' | 'user_experiment';
export type RecommendationStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface OptimizationProject {
  id: string;
  name: string;
  description: string | null;
  material_system: string | null;
  objective_variable: string | null;
  objective_direction: 'maximize' | 'minimize' | null;
  constraints_note: string | null;
  n_literature_points: number;
  n_user_experiments: number;
  n_recommendations: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectVariable {
  id: string;
  project_id: string;
  name: string;
  label: string | null;
  role: VariableRole;
  var_type: VariableType;
  unit: string | null;
  description: string | null;
  min_value: number | null;
  max_value: number | null;
  choices: string[] | null;
  is_objective: boolean;
  is_constraint: boolean;
  created_at: string;
}

export interface UserExperiment {
  id: string;
  project_id: string;
  name: string | null;
  notes: string | null;
  source_type: SourceType;
  status: ExperimentStatus;
  input_values: Record<string, { value: number | string; unit?: string }> | null;
  output_values: Record<string, { value: number | string; unit?: string }> | null;
  objective_value: number | null;
  from_recommendation_id: string | null;
  run_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface RecommendedCandidate {
  id: string;
  run_id: string;
  rank: number;
  proposed_inputs: Record<string, number | string> | null;
  predicted_mean: number | null;
  predicted_std: number | null;
  acquisition_score: number | null;
  explanation: string | null;
  supporting_paper_ids: string[] | null;
  was_executed: boolean;
  executed_experiment_id: string | null;
  created_at: string;
}

export interface RecommendationRun {
  id: string;
  project_id: string;
  status: RecommendationStatus;
  message: string | null;
  n_literature_points: number;
  n_user_points: number;
  n_candidates: number;
  model_type: string | null;
  acquisition_fn: string | null;
  created_at: string;
  completed_at: string | null;
  candidates?: RecommendedCandidate[];
}

export interface DatasetPreview {
  n_total: number;
  n_literature: number;
  n_user: number;
  stats: Record<string, {
    n: number; min: number | null; max: number | null;
    mean: number | null; std: number | null;
  }>;
  points: Record<string, unknown>[];
}

export interface LiteraturePreview {
  n_papers: number;
  papers: Array<{
    paper_id: string;
    paper_title: string;
    paper_year: number | null;
    source_type: SourceType;
    variables_present: string[];
    n_variables: number;
  }>;
}
