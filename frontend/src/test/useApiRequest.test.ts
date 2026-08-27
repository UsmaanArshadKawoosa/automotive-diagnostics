import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import useApiRequest from '../hooks/useApiRequest';

describe('useApiRequest', () => {
  it('returns data from successful request', async () => {
    const fn = vi.fn().mockResolvedValue('result');
    const { result } = renderHook(() => useApiRequest<string, []>(fn));

    await act(async () => {
      await result.current[0]();
    });

    const state = result.current[1];
    expect(state.loading).toBe(false);
    expect(state.data).toBe('result');
    expect(state.error).toBe(null);
  });

  it('returns error from failed request', async () => {
    const fn = vi.fn().mockRejectedValue(new Error('failed'));
    const { result } = renderHook(() => useApiRequest<string, []>(fn));

    await act(async () => {
      await result.current[0]();
    });

    const state = result.current[1];
    expect(state.loading).toBe(false);
    expect(state.data).toBe(null);
    expect(state.error).toBe('failed');
  });

  it('resets state when reset is called', async () => {
    const fn = vi.fn().mockResolvedValue('result');
    const { result } = renderHook(() => useApiRequest<string, []>(fn));

    await act(async () => {
      await result.current[0]();
    });

    let state = result.current[1];
    expect(state.data).toBe('result');

    act(() => {
      result.current[1].reset();
    });

    state = result.current[1];
    expect(state.data).toBe(null);
    expect(state.loading).toBe(false);
    expect(state.error).toBe(null);
  });
});
