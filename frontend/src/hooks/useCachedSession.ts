import { useState, useEffect, useCallback } from 'react';
import type { DiagnosticResult, DiagnosticSession, DiagnosticConversationMessage } from '../types/api';

interface CachedSession {
  sessionId: string;
  cachedAt: string;
  data: {
    session: Omit<DiagnosticSession, 'results' | 'conversation_messages'>;
    results: DiagnosticResult[];
    conversation_messages: DiagnosticConversationMessage[];
    evidence: Array<{
      id: string;
      category: string;
      content: string;
      similarity_score: number;
      source?: string;
      entry_key?: string;
    }>;
  };
}

const CACHE_KEY_PREFIX = 'autodiag_cache_';
const CACHE_TTL_MS = 24 * 60 * 60 * 1000;

export function useCachedSession(sessionId: string | null) {
  const [cachedSession, setCachedSession] = useState<CachedSession | null>(null);
  const [isFromCache, setIsFromCache] = useState(false);

  const saveToCache = useCallback((data: CachedSession['data'], sid: string) => {
    try {
      const cacheEntry: CachedSession = {
        sessionId: sid,
        cachedAt: new Date().toISOString(),
        data,
      };
      localStorage.setItem(`${CACHE_KEY_PREFIX}${sid}`, JSON.stringify(cacheEntry));
      setCachedSession(cacheEntry);
      setIsFromCache(true);
    } catch {
      // localStorage may be full or unavailable
    }
  }, []);

  const loadFromCache = useCallback((sid: string): CachedSession | null => {
    try {
      const raw = localStorage.getItem(`${CACHE_KEY_PREFIX}${sid}`);
      if (!raw) return null;
      const parsed = JSON.parse(raw) as CachedSession;
      const cachedAt = new Date(parsed.cachedAt).getTime();
      if (Date.now() - cachedAt > CACHE_TTL_MS) {
        localStorage.removeItem(`${CACHE_KEY_PREFIX}${sid}`);
        return null;
      }
      return parsed;
    } catch {
      return null;
    }
  }, []);

  const clearCache = useCallback((sid: string) => {
    try {
      localStorage.removeItem(`${CACHE_KEY_PREFIX}${sid}`);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    if (!sessionId) {
      setCachedSession(null);
      setIsFromCache(false);
      return;
    }
    const cached = loadFromCache(sessionId);
    if (cached) {
      setCachedSession(cached);
      setIsFromCache(true);
    } else {
      setCachedSession(null);
      setIsFromCache(false);
    }
  }, [sessionId, loadFromCache]);

  return {
    cachedSession,
    isFromCache,
    saveToCache,
    clearCache,
  };
}
