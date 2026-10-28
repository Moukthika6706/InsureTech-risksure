import { useEffect, useState } from 'react'
import { API_URL, getHealth } from './api'

// Step 2 hello-world: proves the frontend can reach the deployed backend.
export default function App() {
  const [health, setHealth] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getHealth().then(setHealth).catch((e) => setError(e.message))
  }, [])

  return (
    <main className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="bg-white rounded-xl shadow p-8 max-w-md w-full">
        <h1 className="text-3xl font-bold text-indigo-700">RiskSure</h1>
        <p className="text-slate-500 mt-1">P&amp;C quoting, rating &amp; underwriting</p>
        <div className="mt-6 text-sm">
          <span className="font-medium">API: </span>
          {health && <span className="text-green-600">connected (v{health.version})</span>}
          {error && <span className="text-red-600">not reachable: {error}</span>}
          {!health && !error && <span className="text-slate-400">checking...</span>}
          <p className="text-slate-400 mt-1 break-all">{API_URL}</p>
        </div>
      </div>
    </main>
  )
}
