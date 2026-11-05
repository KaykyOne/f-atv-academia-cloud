import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RotateCw } from 'lucide-react'
import { toast } from 'sonner'
import { DataTable, type Coluna } from '@/components/data-table'
import { PageHeader } from '@/components/page-header'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { api, post, type Evento } from '@/lib/api'
import { formatDate } from '@/lib/utils'

const variante = { entregue: 'success', pendente: 'warning', falho: 'destructive' } as const

export function EventosPage() {
  const qc = useQueryClient()
  const eventos = useQuery({ queryKey: ['eventos'], queryFn: () => api<Evento[]>('eventos'), refetchInterval: 3000 })
  const reenviar = useMutation({
    mutationFn: (id: string) => post(`eventos/${id}/reprocessar`),
    onSuccess: () => { toast.info('Evento reenviado. O consumidor deve reconhecê-lo como duplicado.'); qc.invalidateQueries({ queryKey: ['eventos'] }) },
    onError: (e: Error) => toast.error(e.message),
  })
  const contar = (s: Evento['status']) => eventos.data?.filter((e) => e.status === s).length ?? 0

  const colunas: Coluna<Evento>[] = [
    { header: 'Evento', cell: (e) => <div><div className="font-medium">{e.tipo}</div><div className="text-muted-foreground font-mono text-xs">{e.id.slice(0, 8)}…</div></div> },
    { header: 'Status', cell: (e) => <Badge variant={variante[e.status]}>{e.status}</Badge> },
    { header: 'Tentativas', cell: (e) => <span className="tabular-nums">{e.tentativas}</span> },
    { header: 'Criado em', cell: (e) => formatDate(e.criado_em) },
    { header: 'Entregue em', cell: (e) => formatDate(e.entregue_em) },
    { header: 'Último erro', cell: (e) => <span className="text-muted-foreground block max-w-56 truncate text-xs" title={e.ultimo_erro ?? ''}>{e.ultimo_erro ?? '—'}</span> },
    { header: '', className: 'text-right', cell: (e) => (
      <Button variant="outline" size="sm" onClick={() => reenviar.mutate(e.id)} disabled={reenviar.isPending}><RotateCw />Reenviar</Button>
    ) },
  ]

  return (
    <>
      <PageHeader title="Eventos (outbox)" description="Gravados na mesma transação da matrícula e entregues pelo publicador ao serviço de notificações. Atualiza a cada 3 s." />
      <div className="grid gap-4 sm:grid-cols-3">
        {(['pendente', 'entregue', 'falho'] as const).map((s) => (
          <Card key={s} className="gap-1 py-4">
            <CardHeader className="px-4"><CardDescription className="capitalize">{s}</CardDescription><CardTitle className="text-2xl tabular-nums">{contar(s)}</CardTitle></CardHeader>
          </Card>
        ))}
      </div>
      <DataTable dados={eventos.data} carregando={eventos.isPending} colunas={colunas} chave={(e) => e.id}
        busca={(e) => `${e.id} ${e.status} ${e.tipo}`} placeholderBusca="Buscar por ID ou status…" vazio="Nenhum evento. Crie uma matrícula para gerar o primeiro." />
    </>
  )
}
