import { useCallback } from 'react';
import {
  analyzeDiagnostic,
  analyzeInSession,
  listSessions,
  getSession,
  updateHypothesisOutcome,
  createCheckOutcome,
  updateCheckOutcome,
  getAnalytics,
} from '../api/diagnostics';
import useApiRequest from './useApiRequest';
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

export function useAnalyze() {
  const [execute, state] = useApiRequest<DiagnosticAnalyzeResponse, [DiagnosticAnalyzeRequest]>(
    analyzeDiagnostic
  );
  return {
    analyze: execute,
    ...state,
  };
}

export function useAnalyzeInSession() {
  const [execute, state] = useApiRequest<
    DiagnosticAnalyzeResponse,
    [string, DiagnosticAnalyzeRequest]
  >(analyzeInSession);
  return {
    analyzeInSession: useCallback(
      (sessionId: string, payload: DiagnosticAnalyzeRequest) => execute(sessionId, payload),
      [execute]
    ),
    ...state,
  };
}

export function useSessions() {
  const [execute, state] = useApiRequest<DiagnosticSession[], []>(listSessions);
  return {
    loadSessions: execute,
    ...state,
  };
}

export function useSession() {
  const [execute, state] = useApiRequest<DiagnosticSession, [string]>(getSession);
  return {
    loadSession: execute,
    ...state,
  };
}

export function useUpdateOutcome() {
  const [execute, state] = useApiRequest<
    DiagnosticResult,
    [string, HypothesisOutcomeUpdate]
  >(updateHypothesisOutcome);
  return {
    updateOutcome: execute,
    ...state,
  };
}

export function useCreateCheck() {
  const [execute, state] = useApiRequest<
    DiagnosticCheckOutcome,
    [string, DiagnosticCheckOutcomeCreate]
  >(createCheckOutcome);
  return {
    createCheck: execute,
    ...state,
  };
}

export function useUpdateCheck() {
  const [execute, state] = useApiRequest<
    DiagnosticCheckOutcome,
    [string, DiagnosticCheckOutcomeUpdate]
  >(updateCheckOutcome);
  return {
    updateCheck: execute,
    ...state,
  };
}

export function useAnalytics() {
  const [execute, state] = useApiRequest<AnalyticsOutcomes, []>(getAnalytics);
  return {
    loadAnalytics: execute,
    ...state,
  };
}
