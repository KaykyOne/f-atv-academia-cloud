import { useQuery } from '@tanstack/react-query'
import { ConfirmDelete } from '@/components/confirm-delete'
import { DataTable, type Coluna } from '@/components/data-table'
import { FormDialog } from '@/components/form-dialog'
import { PageHeader } from '@/components/page-header'
import { SomenteLeitura } from '@/components/readonly-notice'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useAuth } from '@/hooks/use-auth'
import { useRecurso } from '@/hooks/use-recurso'
import { api, type Aluno, type Disciplina, type Matricula } from '@/lib/api'

export function MatriculasPage() {
  const { usuario } = useAuth()
  const pode = !!usuario?.permissoes.matriculas
  const { lista, criar, excluir } = useRecurso<Matricula>('matriculas')
  const alunos = useQuery({ queryKey: ['alunos'], queryFn: () => api<Aluno[]>('alunos') })
  const disciplinas = useQuery({ queryKey: ['disciplinas'], queryFn: () => api<Disciplina[]>('disciplinas') })

  const colunas: Coluna<Matricula>[] = [
    { header: 'Aluno', cell: (m) => <span className="font-medium">{m.aluno}</span> },
    { header: 'Disciplina', cell: (m) => m.disciplina },
    { header: 'Nº', cell: (m) => <span className="text-muted-foreground font-mono text-xs">#{m.id}</span> },
    ...(pode ? [{ header: '', className: 'w-12 text-right', cell: (m: Matricula) => (
      <ConfirmDelete titulo="Cancelar matrícula?" descricao={`${m.aluno} será desmatriculado(a) de ${m.disciplina}.`}
        onConfirm={() => excluir.mutate(m.id)} />
    ) }] : []),
  ]

  return (
    <>
      <PageHeader title="Matrículas" description="Cada matrícula gera um evento que dispara a notificação ao aluno."
        actions={pode ? (
          <FormDialog rotulo="Nova matrícula" titulo="Nova matrícula" descricao="A mesma matrícula não pode ser repetida."
            onSubmit={(f) => criar.mutateAsync({ aluno_id: Number(f.get('aluno_id')), disciplina_id: Number(f.get('disciplina_id')) })}>
            <div className="grid gap-2">
              <Label>Aluno</Label>
              <Select name="aluno_id" required>
                <SelectTrigger aria-label="Aluno"><SelectValue placeholder="Selecione o aluno" /></SelectTrigger>
                <SelectContent>{alunos.data?.map((a) => <SelectItem key={a.id} value={String(a.id)}>{a.nome}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label>Disciplina</Label>
              <Select name="disciplina_id" required>
                <SelectTrigger aria-label="Disciplina"><SelectValue placeholder="Selecione a disciplina" /></SelectTrigger>
                <SelectContent>{disciplinas.data?.map((d) => <SelectItem key={d.id} value={String(d.id)}>{d.nome}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </FormDialog>
        ) : <SomenteLeitura />} />
      <DataTable dados={lista.data} carregando={lista.isPending} colunas={colunas} chave={(m) => m.id}
        busca={(m) => `${m.aluno} ${m.disciplina}`} placeholderBusca="Buscar por aluno ou disciplina…" vazio="Nenhuma matrícula encontrada." />
    </>
  )
}
