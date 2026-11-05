import { useQuery } from '@tanstack/react-query'
import { Mail } from 'lucide-react'
import { DataTable, type Coluna } from '@/components/data-table'
import { PageHeader } from '@/components/page-header'
import { api, type Notificacao } from '@/lib/api'
import { formatDate } from '@/lib/utils'

export function NotificacoesPage() {
  const q = useQuery({ queryKey: ['notificacoes'], queryFn: () => api<Notificacao[]>('notificacoes'), refetchInterval: 5000 })
  const colunas: Coluna<Notificacao>[] = [
    { header: 'Destinatário', cell: (n) => <span className="inline-flex items-center gap-2 font-medium"><Mail className="text-muted-foreground size-4" />{n.destinatario}</span> },
    { header: 'Mensagem', cell: (n) => <span className="block max-w-md truncate" title={n.mensagem}>{n.mensagem}</span> },
    { header: 'Evento', cell: (n) => <span className="text-muted-foreground font-mono text-xs">{n.evento_id.slice(0, 8)}…</span> },
    { header: 'Recebida em', cell: (n) => formatDate(n.recebido_em) },
  ]
  return (
    <>
      <PageHeader title="Notificações simuladas" description="Registradas pelo serviço de notificações (nenhum e-mail real é enviado). Cada evento gera no máximo uma notificação." />
      {q.isError ? (
        <div className="border-destructive/30 bg-destructive/5 text-destructive rounded-lg border p-4 text-sm">{(q.error as Error).message}</div>
      ) : (
        <DataTable dados={q.data} carregando={q.isPending} colunas={colunas} chave={(n) => n.id}
          busca={(n) => `${n.destinatario} ${n.mensagem}`} placeholderBusca="Buscar destinatário ou mensagem…" vazio="Nenhuma notificação registrada." />
      )}
    </>
  )
}
