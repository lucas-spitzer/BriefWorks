import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabaseClient'

export function AuthCallbackPage() {
  const navigate = useNavigate()
  const [message, setMessage] = useState('Completing secure login.')

  useEffect(() => {
    async function handleCallback() {
      const params = new URLSearchParams(window.location.search)
      const code = params.get('code')

      const { error } = code
        ? await supabase.auth.exchangeCodeForSession(code)
        : await supabase.auth.getSession()

      if (error) {
        console.error('Authentication callback failed:', error)
        setMessage('Authentication failed. Returning to login.')
        navigate('/login', { replace: true })
        return
      }

      navigate('/app', { replace: true })
    }

    void handleCallback()
  }, [navigate])

  return (
    <main className="status-page" aria-live="polite">
      <section className="status-card">
        <p className="eyebrow">BriefWorks</p>
        <h1>Secure Login</h1>
        <p>{message}</p>
      </section>
    </main>
  )
}
