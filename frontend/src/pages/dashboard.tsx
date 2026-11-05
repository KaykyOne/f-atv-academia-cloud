import { Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, BookOpen, ClipboardList, Server, Users, type LucideIcon } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { nomePerfil, useAuth } from '@/hooks/use-auth'
import { api, type Matricula, type Resumo } from '@/lib/api'

function Stat({ titulo, valor, icon: Icon, to }: { titulo: string; valor?: number; icon: LucideIcon; to: string }) {
  return (
    <Card className="gap-2">
      <CardHeader>
        <CardDescription>{titulo}</CardDescription>
        <CardAction><Icon className="text-muted-foreground size-4" /></CardAction>
        <CardTitle className="text-3xl tabular-nums">{valor ?? <Skeleton className="h-8 w-12" />}</CardTitle>
      </CardHeader>
      <CardContent>
        <Link to={to} className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 text-xs">Ver todos <ArrowRight className="size-3" /></Link>
      </CardContent>
    </Card>
  )
}

export function DashboardPage() {
  const { usuario } = useAuth()
  const resumo = useQuery({ queryKey: ['resumo'], queryFn: () => api<Resumo>('resumo') })
  const matriculas = useQuery({ queryKey: ['matriculas'], queryFn: () => api<Matricula[]>('matriculas') })
  const recentes = [...(matriculas.data ?? [])].reverse().slice(0, 5)

  return (
    <>
      <PageHeader title={`Olá, ${usuario?.nome.split(' ')[0]}`} description={`Você está conectado como ${nomePerfil[usuario?.perfil ?? '']}.`} />
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat titulo="Alunos" valor={resumo.data?.alunos} icon={Users} to="/alunos" />
        <Stat titulo="Disciplinas" valor={resumo.data?.disciplinas} icon={BookOpen} to="/disciplinas" />
        <Stat titulo="Matrículas" valor={resumo.data?.matriculas} icon={ClipboardList} to="/matriculas" />
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Matrículas recentes</CardTitle>
            <CardDescription>Últimos vínculos entre alunos e disciplinas</CardDescription>
            <CardAction><Button variant="outline" size="sm" asChild><Link to="/matriculas">Abrir</Link></Button></CardAction>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader><TableRow><TableHead>Aluno</TableHead><TableHead>Disciplina</TableHead></TableRow></TableHeader>
              <TableBody>
                {recentes.length ? recentes.map((m) => (
                  <TableRow key={m.id}><TableCell className="font-medium">{m.aluno}</TableCell><TableCell>{m.disciplina}</TableCell></TableRow>
                )) : (
                  <TableRow><TableCell colSpan={2} className="text-muted-foreground h-20 text-center">{matriculas.isPending ? 'Carregando…' : 'Nenhuma matrícula ainda.'}</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Infraestrutura</CardTitle>
            <CardDescription>Quem atendeu esta requisição</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Réplica web</span>
              <Badge variant="outline" className="font-mono"><Server />{resumo.data?.instancia ?? '…'}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Banco de dados</span>
              <Badge variant={resumo.isError ? 'destructive' : 'success'}>{resumo.isError ? 'Indisponível' : 'Conectado'}</Badge>
            </div>
            <p className="text-muted-foreground text-xs">O balanceador alterna entre as réplicas: recarregue a página para ver a instância mudar.</p>
          </CardContent>
        </Card>
      </div>
    </>
  )
}
