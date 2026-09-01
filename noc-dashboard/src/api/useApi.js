import { useState, useEffect, useCallback } from 'react';

/**
 * Generic data-fetching hook.
 * @param {Function} fetcher  — async function that returns data
 * @param {Array}    deps     — dependency array (like useEffect)
 * @param {boolean}  skip     — set true to not fetch yet
 */
export function useApi(fetcher, deps = [], skip = false) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(!skip);
  const [error, setError] = useState(null);

  const execute = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher();
      setData(result);
    } catch (err) {
      setError(err.message || 'Unknown error');
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    if (!skip) execute();
  }, [execute, skip]);

  return { data, loading, error, refetch: execute };
}
