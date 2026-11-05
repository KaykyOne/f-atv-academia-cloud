// Cliente da API do AcademiaCloud (mesma origem; cookie de sessão HttpOnly).
export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message) }
}

export async function api<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  const r = await fetch('/api/' + path, {
    ...options,
    credentials: 'same-origin',
    // Toda alteração vai como JSON: o backend recusa outros formatos (proteção CSRF).
    headers: { 'Content-Type': 'application/json', ...options.headers },
  })
  if (r.status === 204) return null as T
  const data = await r.json().catch(() => ({}))
  if (!r.ok) throw new ApiError(r.status, data.erro || 'Falha na requisição.')
  return data as T
}

export const post = <T,>(path: string, body: unknown = {}) => api<T>(path, { method: 'POST', body: JSON.stringify(body) })
export const del = (path: string) => api<null>(path, { method: 'DELETE' })

export type Perfil = 'administrador' | 'secretaria' | 'professor'
export type Entidade = 'alunos' | 'disciplinas' | 'matriculas'

export interface Usuario {
  id: number; login: string; nome: string; perfil: Perfil
  permissoes: Record<Entidade, boolean>; administrador: boolean
}
export interface Aluno { id: number; nome: string; email: string }
export interface Disciplina { id: number; nome: string; carga_horaria: number }
export interface Matricula { id: number; aluno_id: number; disciplina_id: number; aluno: string; disciplina: string }
export interface Resumo { alunos: number; disciplinas: number; matriculas: number; instancia: string }
export interface Evento {
  id: string; tipo: string; status: 'pendente' | 'entregue' | 'falho'; tentativas: number
  ultimo_erro: string | null; criado_em: string; entregue_em: string | null
}
export interface Notificacao { id: number; evento_id: string; tipo: string; destinatario: string; mensagem: string; recebido_em: string; instancia: string }
export interface RegistroAuditoria {
  id: number; quando: string; usuario: string | null; perfil: string | null; acao: string
  recurso: string | null; resultado: string; detalhe: string | null; ip: string | null; instancia: string | null
}
