import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api, del, post, type Entidade } from '@/lib/api'

// Lista + criar + excluir de um recurso acadêmico, com toasts e invalidação de cache.
export function useRecurso<T>(entidade: Entidade) {
  const qc = useQueryClient()
  const invalidar = () => Promise.all([
    qc.invalidateQueries({ queryKey: [entidade] }),
    qc.invalidateQueries({ queryKey: ['resumo'] }),
    qc.invalidateQueries({ queryKey: ['matriculas'] }),
  ])
  const lista = useQuery({ queryKey: [entidade], queryFn: () => api<T[]>(entidade) })
  const criar = useMutation({
    mutationFn: (dados: Record<string, unknown>) => post<T>(entidade, dados),
    onSuccess: () => { toast.success('Cadastro realizado.'); return invalidar() },
    onError: (e: Error) => toast.error(e.message),
  })
  const excluir = useMutation({
    mutationFn: (id: number) => del(`${entidade}/${id}`),
    onSuccess: () => { toast.success('Registro excluído.'); return invalidar() },
    onError: (e: Error) => toast.error(e.message),
  })
  return { lista, criar, excluir }
}
