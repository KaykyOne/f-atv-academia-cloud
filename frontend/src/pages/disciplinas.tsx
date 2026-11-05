import { ConfirmDelete } from '@/components/confirm-delete'
import { DataTable, type Coluna } from '@/components/data-table'
import { FormDialog } from '@/components/form-dialog'
import { PageHeader } from '@/components/page-header'
import { SomenteLeitura } from '@/components/readonly-notice'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuth } from '@/hooks/use-auth'
import { useRecurso } from '@/hooks/use-recurso'
import type { Disciplina } from '@/lib/api'

export function DisciplinasPage() {
  const { usuario } = useAuth()
  const pode = !!usuario?.permissoes.disciplinas
  const { lista, criar, excluir } = useRecurso<Disciplina>('disciplinas')

  const colunas: Coluna<Disciplina>[] = [
    { header: 'Disciplina', cell: (d) => <span className="font-medium">{d.nome}</span> },
    { header: 'Carga horária', cell: (d) => <Badge variant="secondary">{d.carga_horaria} h</Badge> },
    ...(pode ? [{ header: '', className: 'w-12 text-right', cell: (d: Disciplina) => (
      <ConfirmDelete titulo={`Excluir ${d.nome}?`} descricao="Disciplinas com alunos matriculados não podem ser excluídas."
        onConfirm={() => excluir.mutate(d.id)} />
    ) }] : []),
  ]

  return (
    <>
      <PageHeader title="Disciplinas" description="Componentes curriculares oferecidos."
        actions={pode ? (
          <FormDialog rotulo="Nova disciplina" titulo="Nova disciplina" descricao="Informe o nome e a carga horária."
            onSubmit={(f) => criar.mutateAsync({ nome: f.get('nome'), carga_horaria: Number(f.get('carga_horaria')) })}>
            <div className="grid gap-2"><Label htmlFor="nome">Nome</Label><Input id="nome" name="nome" required minLength={2} maxLength={100} placeholder="Ex.: Redes de Computadores" /></div>
            <div className="grid gap-2"><Label htmlFor="carga">Carga horária (h)</Label><Input id="carga" name="carga_horaria" type="number" min={1} max={1000} defaultValue={40} required /></div>
          </FormDialog>
        ) : <SomenteLeitura />} />
      <DataTable dados={lista.data} carregando={lista.isPending} colunas={colunas} chave={(d) => d.id}
        busca={(d) => d.nome} placeholderBusca="Buscar disciplina…" vazio="Nenhuma disciplina encontrada." />
    </>
  )
}
