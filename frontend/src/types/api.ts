export type VehicleType = 'hatchback' | 'sedan' | 'suv' | 'pickup' | 'van';

export type Severity = 'low' | 'medium' | 'high' | 'critical';

export type HypothesisStatus = 'proposed' | 'investigating' | 'confirmed' | 'rejected';

export type CheckStatus = 'recommended' | 'performed' | 'passed' | 'failed';

export interface KnowledgeSearchResult {
  id: string;
  category: string;
  entry_key: string | null;
  content: string;
  source: string | null;
  similarity_score: number;
}

export interface EvidenceReference {
  evidence_id: string;
  category: string;
  entry_key: string | null;
  excerpt: string;
  similarity_score: number;
  relevance: 'supporting' | 'conflicting' | 'contextual';
}

export type EvidenceQuality = 'strong' | 'moderate' | 'weak' | 'insufficient';

export interface DIYRepairGuidance {
  suitable: boolean;
  suitability: string;
  difficulty?: 'easy' | 'moderate' | 'advanced';
  estimated_time?: string | null;
  tools: string[];
  parts: string[];
  safety_warnings: string[];
  preparation_steps: string[];
  steps: string[];
  verification_steps: string[];
  professional_help_conditions: string[];
}

export interface ResourceLink {
  type: 'guide' | 'youtube';
  title: string;
  source: string;
  url: string;
}

export interface DiagnosticHypothesis {
  fault_description: string;
  confidence_score: number;
  severity: Severity;
  supporting_evidence: string[];
  recommended_checks: string[];
  repair_suggestion: string | null;
  knowledge_references: string[];
  component_id?: string;
  system_category?: string;
  vehicle_region?: string;
  safety_tier?: RepairSafetyTier;
  safety_tier_label?: string;
  safety_tier_description?: string;
  safety_tier_reasoning?: string[];
  evidence_references: EvidenceReference[];
  differential_rank?: number;
  evidence_quality?: EvidenceQuality;
  diy_repair?: DIYRepairGuidance | null;
  resources?: ResourceLink[];
}

export interface DiagnosticAnalyzeResponse {
  session_id: string;
  vehicle: Record<string, string | number | null>;
  query: string;
  evidence: KnowledgeSearchResult[];
  hypotheses: DiagnosticHypothesis[];
  status: 'complete' | 'needs_more_information';
  follow_up_question?: string;
  follow_up_reason?: string;
}

export interface DiagnosticCheckOutcome {
  id: string;
  result_id: string;
  check_description: string;
  status: CheckStatus;
  observed_result: string | null;
  technician_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface DiagnosticResult {
  id: string;
  session_id: string;
  created_at: string;
  fault_description: string;
  confidence_score: number;
  repair_suggestion: string | null;
  severity: Severity | null;
  hypothesis_status: HypothesisStatus;
  observed_result: string | null;
  recommended_checks: string[];
  supporting_evidence: string[];
  knowledge_references: string[];
  check_outcomes: DiagnosticCheckOutcome[];
  component_id?: string;
  system_category?: string;
  vehicle_region?: string;
  safety_tier?: RepairSafetyTier;
  safety_tier_label?: string;
  safety_tier_description?: string;
  safety_tier_reasoning?: string[];
  differential_rank?: number;
  evidence_quality?: string;
  diy_repair?: DIYRepairGuidance | null;
  resources?: ResourceLink[];
}

export interface DiagnosticSession {
  id: string;
  created_at: string;
  updated_at: string;
  vin: string | null;
  make: string | null;
  model: string | null;
  year: number | null;
  symptom_text: string;
  dtc_codes: string | null;
  results: DiagnosticResult[];
  conversation_messages: DiagnosticConversationMessage[];
}

export interface DiagnosticConversationMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  turn_index: number;
  created_at: string;
}

export interface DiagnosticAnalyzeRequest {
  vin?: string;
  make?: string;
  model?: string;
  year?: number;
  vehicle_type?: VehicleType;
  dtc_codes?: string[];
  symptom_text: string;
  session_id?: string;
  follow_up_answer?: string;
}

export interface HypothesisOutcomeUpdate {
  hypothesis_status: HypothesisStatus;
  observed_result?: string;
}

export interface DiagnosticCheckOutcomeCreate {
  check_description: string;
  status?: CheckStatus;
  observed_result?: string;
  technician_note?: string;
}

export interface DiagnosticCheckOutcomeUpdate {
  status?: CheckStatus;
  observed_result?: string;
  technician_note?: string;
}

export interface AnalyticsOutcomes {
  total_sessions: number;
  total_results: number;
  hypothesis_status_distribution: Record<string, number>;
  check_status_distribution: Record<string, number>;
  common_dtcs: { code: string; count: number }[];
  confirmed_faults: { fault_description: string; count: number }[];
}

export interface ApiError {
  detail: string | { msg: string; type: string }[];
}

export type RepairSafetyTier = 'diy_inspection' | 'diy_repair' | 'mechanic_recommended' | 'immediate_professional';

// TODO: Repair safety tier will be populated by a future rules engine.
// It will be derived from severity, component_id, and repair complexity,
// not generated by the LLM.
