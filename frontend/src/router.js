// Minimal hash router: "#/quote/auto" -> ["quote", "auto"]. Hash URLs need no
// server rewrites and keep the app dependency-free.
import { useEffect, useState } from 'react'

const parse = () => window.location.hash.replace(/^#\/?/, '').split('/').filter(Boolean)

export function useRoute() {
  const [parts, setParts] = useState(parse)
  useEffect(() => {
    const onChange = () => {
      setParts(parse())
      window.scrollTo(0, 0)
    }
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return parts
}

export const navigate = (path) => {
  window.location.hash = path
}
