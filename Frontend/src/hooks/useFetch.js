import { useCallback, useEffect, useState } from 'react';

import api, { errorMessage } from '../services/api';

/** GET a URL and keep {data, loading, error}; call reload() after a change. Pass url=null to skip. */
export default function useFetch(url, params) {
  const [state, setState] = useState({ data: null, loading: Boolean(url), error: null });
  const [tick, setTick] = useState(0);
  const key = `${url}|${JSON.stringify(params || {})}`;

  useEffect(() => {
    if (!url) {
      setState({ data: null, loading: false, error: null });
      return undefined;
    }
    let alive = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    api.get(url, { params })
      .then((r) => alive && setState({ data: r.data, loading: false, error: null }))
      .catch((e) => alive && setState({ data: null, loading: false, error: errorMessage(e) }));
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, reload };
}
