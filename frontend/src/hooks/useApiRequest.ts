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
  const cancelRef = useRef(false);

  const execute = useCallback(
    async (...args: Args) => {
      cancelRef.current = false;
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const result = await fn(...args);
        if (!cancelRef.current) {
          setState({ data: result, loading: false, error: null });
        }
      } catch (err) {
        if (!cancelRef.current) {
          const message = err instanceof Error ? err.message : 'An unexpected error occurred';
          setState((prev) => ({ ...prev, loading: false, error: message }));
        }
      }
    },
    [fn]
  );

  const reset = useCallback(() => {
    cancelRef.current = true;
    setState({ data: null, loading: false, error: null });
  }, []);

  return [execute, { ...state, reset }];
}

export default useApiRequest;
