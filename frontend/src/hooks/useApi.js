import { useEffect, useState } from 'react'
import api from '../api/axios'
import { normalizeApiError } from '../utils/apiError'

/**
 * Simple GET hook.
 *   const { data, loading, error, reload } = useApi('/properties/', { page: 1 })
 * - params badle to naya request jaata hai, purana response ignore hota hai.
 * - enabled=false par request nahi jaati.
 * - loading "derived" hai (response ki key match nahi => loading), isliye effect mein sync setState nahi.
 */
export default function useApi(url, params = {}, { enabled = true } = {}) {
  const [tick, setTick] = useState(0)
  const [state, setState] = useState({ key: null, data: null, error: null })

  const paramsKey = JSON.stringify(params)
  const key = `${url}|${paramsKey}|${tick}`

  useEffect(() => {
    if (!enabled || !url) return undefined
    let cancelled = false

    api
      .get(url, { params: JSON.parse(paramsKey), paramsSerializer: { indexes: null } })
      .then(({ data }) => {
        if (!cancelled) setState({ key, data, error: null })
      })
      .catch((err) => {
        if (!cancelled) setState({ key, data: null, error: normalizeApiError(err) })
      })

    return () => {
      cancelled = true
    }
  }, [url, paramsKey, enabled, key])

  const ready = enabled && state.key === key

  return {
    data: ready ? state.data : null,
    error: ready ? state.error : null,
    loading: enabled && !ready,
    reload: () => setTick((t) => t + 1),
  }
}