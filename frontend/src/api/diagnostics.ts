import { apiClient } from './client';
import type {
  DiagnosticAnalyzeRequest,
  DiagnosticAnalyzeResponse,
  DiagnosticCheckOutcome,
  DiagnosticCheckOutcomeCreate,
  DiagnosticCheckOutcomeUpdate,
  DiagnosticResult,
  DiagnosticSession,
  HypothesisOutcomeUpdate,
  AnalyticsOutcomes,
} from '../types/api';

export async function analyzeDiagnostic(
  payload: DiagnosticAnalyzeRequest
): Promise<DiagnosticAnalyzeResponse> {
  const { data } = await apiClient.post<DiagnosticAnalyzeResponse>('/diagnostics/analyze', payload);
  return data;
}

export async function analyzeInSession(
  sessionId: string,
  payload: DiagnosticAnalyzeRequest
): Promise<DiagnosticAnalyzeResponse> {
  const { data } = await apiClient.post<DiagnosticAnalyzeResponse>(
    `/diagnostics/sessions/${sessionId}/analyze`,
    payload
  );
  return data;
}

export async function createSession(
  payload: { vin?: string; make?: string; model?: string; year?: number; symptom_text: string; dtc_codes?: string }
): Promise<DiagnosticSession> {
  const { data } = await apiClient.post<DiagnosticSession>('/diagnostics/sessions', payload);
  return data;
}

export async function listSessions(skip = 0, limit = 100): Promise<DiagnosticSession[]> {
  const { data } = await apiClient.get<DiagnosticSession[]>(
    `/diagnostics/sessions?skip=${skip}&limit=${limit}`
  );
  return data;
}

export async function getSession(sessionId: string): Promise<DiagnosticSession> {
  const { data } = await apiClient.get<DiagnosticSession>(`/diagnostics/sessions/${sessionId}`);
  return data;
}

export async function getResult(resultId: string): Promise<DiagnosticResult> {
  const { data } = await apiClient.get<DiagnosticResult>(`/diagnostics/results/${resultId}`);
  return data;
}

export async function updateHypothesisOutcome(
  resultId: string,
  payload: HypothesisOutcomeUpdate
): Promise<DiagnosticResult> {
  const { data } = await apiClient.patch<DiagnosticResult>(
    `/diagnostics/results/${resultId}/outcome`,
    payload
  );
  return data;
}

export async function createCheckOutcome(
  resultId: string,
  payload: DiagnosticCheckOutcomeCreate
): Promise<DiagnosticCheckOutcome> {
  const { data } = await apiClient.post<DiagnosticCheckOutcome>(
    `/diagnostics/results/${resultId}/checks`,
    payload
  );
  return data;
}

export async function updateCheckOutcome(
  outcomeId: string,
  payload: DiagnosticCheckOutcomeUpdate
): Promise<DiagnosticCheckOutcome> {
  const { data } = await apiClient.patch<DiagnosticCheckOutcome>(
    `/diagnostics/checks/${outcomeId}`,
    payload
  );
  return data;
}

export async function listCheckOutcomes(resultId: string): Promise<DiagnosticCheckOutcome[]> {
  const { data } = await apiClient.get<DiagnosticCheckOutcome[]>(
    `/diagnostics/results/${resultId}/checks`
  );
  return data;
}

export async function getAnalytics(): Promise<AnalyticsOutcomes> {
  const { data } = await apiClient.get<AnalyticsOutcomes>('/diagnostics/analytics/outcomes');
  return data;
}
