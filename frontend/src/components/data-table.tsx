import { useMemo, useState, type ReactNode } from 'react'
import { Inbox, Search } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { cn } from '@/lib/utils'

export interface Coluna<T> {
  header: string
  cell: (row: T) => ReactNode
  className?: string
}

interface Props<T> {
  dados: T[] | undefined
  colunas: Coluna<T>[]
  carregando?: boolean
  chave: (row: T) => string | number
  busca?: (row: T) => string        // texto pesquisável da linha
  placeholderBusca?: string
  vazio?: string
  toolbar?: ReactNode
}

export function DataTable<T>({ dados, colunas, carregando, chave, busca, placeholderBusca = 'Pesquisar…', vazio = 'Nenhum registro encontrado.', toolbar }: Props<T>) {
  const [termo, setTermo] = useState('')
  const filtrados = useMemo(() => {
    if (!dados || !busca || !termo.trim()) return dados ?? []
    const t = termo.trim().toLowerCase()
    return dados.filter((r) => busca(r).toLowerCase().includes(t))
  }, [dados, busca, termo])

  return (
    <Card className="gap-0 py-0">
      {(busca || toolbar) && (
        <div className="flex flex-col gap-3 border-b p-4 sm:flex-row sm:items-center sm:justify-between">
          {busca && (
            <div className="relative w-full sm:max-w-xs">
              <Search className="text-muted-foreground absolute top-1/2 left-2.5 size-4 -translate-y-1/2" />
              <Input value={termo} onChange={(e) => setTermo(e.target.value)} placeholder={placeholderBusca} className="pl-8" aria-label="Pesquisar" />
            </div>
          )}
          {toolbar}
        </div>
      )}
      <CardContent className="px-2 py-2">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              {colunas.map((c) => <TableHead key={c.header} className={cn('px-3', c.className)}>{c.header}</TableHead>)}
            </TableRow>
          </TableHeader>
          <TableBody>
            {carregando ? (
              Array.from({ length: 4 }).map((_, i) => (
                <TableRow key={i}>{colunas.map((c) => <TableCell key={c.header} className="px-3"><Skeleton className="h-4 w-full max-w-40" /></TableCell>)}</TableRow>
              ))
            ) : filtrados.length === 0 ? (
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={colunas.length} className="h-32 text-center">
                  <div className="text-muted-foreground flex flex-col items-center gap-2"><Inbox className="size-6" />{vazio}</div>
                </TableCell>
              </TableRow>
            ) : (
              filtrados.map((row) => (
                <TableRow key={chave(row)}>
                  {colunas.map((c) => <TableCell key={c.header} className={cn('px-3', c.className)}>{c.cell(row)}</TableCell>)}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </CardContent>
      {!carregando && dados && dados.length > 0 && (
        <div className="text-muted-foreground border-t px-4 py-3 text-xs">
          {filtrados.length} de {dados.length} registro(s)
        </div>
      )}
    </Card>
  )
}
