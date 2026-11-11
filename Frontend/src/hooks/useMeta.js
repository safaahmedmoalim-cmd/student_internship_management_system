import { useEffect, useState } from 'react';

import api from '../services/api';

let cache = null;
let pending = null;

/** Choice lists and assessment criteria from GET /api/meta/ (fetched once per page load). */
export default function useMeta() {
  const [meta, setMeta] = useState(cache);
  useEffect(() => {
    if (cache) return;
    pending = pending || api.get('/meta/').then((r) => { cache = r.data; return cache; });
    pending.then(setMeta).catch(() => { pending = null; });
  }, []);
  return meta;
}
