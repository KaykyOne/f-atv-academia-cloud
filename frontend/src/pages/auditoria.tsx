import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { DataTable, type Coluna } from '@/components/data-table'
import { PageHeader } from '@/components/page-header'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { api, type RegistroAuditoria } from '@/lib/api'
import { formatDate } from '@/lib/utils'

const variante: Record<string, 'success' | 'destructive' | 'warning' | 'secondary'> = {
  sucesso: 'success', falha: 'destructive', negado: 'destructive', bloqueado: 'destructive', conflito: 'warning',
}

export function AuditoriaPage() {
  const [resultado, setResultado] = useState('todos')
  const q = useQuery({ queryKey: ['auditoria'], queryFn: () => api<RegistroAuditoria[]>('auditoria'), refetchInterval: 10_000 })
  const dados = resultado === 'todos' ? q.data : q.data?.filter((r) => r.resultado === resultado)

  const colunas: Coluna<RegistroAuditoria>[] = [
    { header: 'Quando', cell: (r) => <span className="text-muted-foreground">{formatDate(r.quando)}</span> },
    { header: 'Usuário', cell: (r) => <span className="font-medium">{r.usuario ?? '—'}</span> },
    { header: 'Ação', cell: (r) => <code className="bg-muted rounded px-1.5 py-0.5 text-xs">{r.acao}</code> },
    { header: 'Recurso', cell: (r) => r.recurso ?? '—' },
    { header: 'Resultado', cell: (r) => <Badge variant={variante[r.resultado] ?? 'secondary'}>{r.resultado}</Badge> },
    { header: 'Detalhe', cell: (r) => <span className="text-muted-foreground text-xs">{r.detalhe ?? ''}</span> },
    { header: 'IP / instância', cell: (r) => <span className="text-muted-foreground font-mono text-xs">{r.ip} · {r.instancia}</span> },
  ]

  return (
    <>
      <PageHeader title="Auditoria" description="Logins, cadastros, exclusões e acessos negados (últimos 200 registros)." />
      <DataTable dados={dados} carregando={q.isPending} colunas={colunas} chave={(r) => r.id}
        busca={(r) => `${r.usuario} ${r.acao} ${r.recurso} ${r.detalhe}`} placeholderBusca="Buscar usuário, ação…"
        toolbar={
          <Select value={resultado} onValueChange={setResultado}>
            <SelectTrigger className="w-full sm:w-44" aria-label="Filtrar resultado"><SelectValue /></SelectTrigger>
            <SelectContent>
              {['todos', 'sucesso', 'falha', 'negado', 'bloqueado', 'conflito'].map((v) => <SelectItem key={v} value={v} className="capitalize">{v === 'todos' ? 'Todos os resultados' : v}</SelectItem>)}
            </SelectContent>
          </Select>
        } />
    </>
  )
}
