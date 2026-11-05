import { createContext, useContext, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, post, ApiError, type Usuario } from '@/lib/api'

interface AuthState {
  usuario: Usuario | null
  carregando: boolean
  entrar: (usuario: string, senha: string) => Promise<Usuario>
  sair: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient()
  const me = useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      try { return await api<Usuario>('me') }
      catch (e) { if (e instanceof ApiError && e.status === 401) return null; throw e }
    },
    staleTime: 60_000,
  })
  const login = useMutation({
    mutationFn: (c: { usuario: string; senha: string }) => post<Usuario>('login', c),
    onSuccess: (u) => { qc.clear(); qc.setQueryData(['me'], u) },
  })
  const logout = useMutation({
    mutationFn: () => post<null>('logout'),
    onSettled: () => { qc.clear(); qc.setQueryData(['me'], null) },
  })
  return (
    <AuthContext.Provider value={{
      usuario: me.data ?? null,
      carregando: me.isPending,
      entrar: (usuario, senha) => login.mutateAsync({ usuario, senha }),
      sair: async () => { await logout.mutateAsync().catch(() => {}) },
    }}>{children}</AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth fora do AuthProvider')
  return ctx
}

export const nomePerfil: Record<string, string> = {
  administrador: 'Administrador', secretaria: 'Secretaria', professor: 'Professor',
}
