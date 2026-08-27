import { useState, useCallback, useRef } from 'react';

interface RequestState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

function useApiRequest<T, Args extends unknown[]>(
  fn: (...args: Args) => Promise<T>
): [(...args: Args) => Promise<void>, RequestState<T> & { reset: () => void }] {
  const [state, setState] = useState<RequestState<T>>({
    data: null,
    loading: false,
    error: null,
  });
  const requestIdRef = useRef(0);

  const execute = useCallback(
    async (...args: Args) => {
      const currentRequestId = ++requestIdRef.current;
      setState({ data: null, loading: true, error: null });
      try {
        const result = await fn(...args);
        if (currentRequestId === requestIdRef.current) {
          setState({ data: result, loading: false, error: null });
        }
      } catch (err) {
        if (currentRequestId === requestIdRef.current) {
          const message = err instanceof Error ? err.message : 'An unexpected error occurred';
          setState({ data: null, loading: false, error: message });
        }
      }
    },
    [fn]
  );

  const reset = useCallback(() => {
    requestIdRef.current = 0;
    setState({ data: null, loading: false, error: null });
  }, []);

  return [execute, { ...state, reset }];
}

export default useApiRequest;
