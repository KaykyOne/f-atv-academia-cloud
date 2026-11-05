import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from '@/components/ui/sonner'
import { AuthProvider } from '@/hooks/use-auth'
import { ApiError } from '@/lib/api'
import App from '@/App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      // Não insiste em 401/403/404; tenta de novo em falhas transitórias (ex.: réplica caindo).
      retry: (n, e) => !(e instanceof ApiError && [401, 403, 404].includes(e.status)) && n < 2,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <App />
        <Toaster />
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
)
