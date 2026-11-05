import { ConfirmDelete } from '@/components/confirm-delete'
import { DataTable, type Coluna } from '@/components/data-table'
import { FormDialog } from '@/components/form-dialog'
import { PageHeader } from '@/components/page-header'
import { SomenteLeitura } from '@/components/readonly-notice'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuth } from '@/hooks/use-auth'
import { useRecurso } from '@/hooks/use-recurso'
import type { Aluno } from '@/lib/api'

export function AlunosPage() {
  const { usuario } = useAuth()
  const pode = !!usuario?.permissoes.alunos
  const { lista, criar, excluir } = useRecurso<Aluno>('alunos')

  const colunas: Coluna<Aluno>[] = [
    { header: 'Nome', cell: (a) => <span className="font-medium">{a.nome}</span> },
    { header: 'E-mail', cell: (a) => <span className="text-muted-foreground">{a.email}</span> },
    ...(pode ? [{ header: '', className: 'w-12 text-right', cell: (a: Aluno) => (
      <ConfirmDelete titulo={`Excluir ${a.nome}?`} descricao="O aluno será removido. Alunos com matrícula ativa não podem ser excluídos: cancele a matrícula antes."
        onConfirm={() => excluir.mutate(a.id)} />
    ) }] : []),
  ]

  return (
    <>
      <PageHeader title="Alunos" description="Cadastro de alunos da instituição."
        actions={pode ? (
          <FormDialog rotulo="Novo aluno" titulo="Novo aluno" descricao="Use somente dados fictícios."
            onSubmit={(f) => criar.mutateAsync({ nome: f.get('nome'), email: f.get('email') })}>
            <div className="grid gap-2"><Label htmlFor="nome">Nome</Label><Input id="nome" name="nome" required minLength={2} maxLength={100} placeholder="Ex.: Carla Exemplo" /></div>
            <div className="grid gap-2"><Label htmlFor="email">E-mail</Label><Input id="email" name="email" type="email" required maxLength={160} placeholder="carla@example.test" /></div>
          </FormDialog>
        ) : <SomenteLeitura />} />
      <DataTable dados={lista.data} carregando={lista.isPending} colunas={colunas} chave={(a) => a.id}
        busca={(a) => `${a.nome} ${a.email}`} placeholderBusca="Buscar por nome ou e-mail…" vazio="Nenhum aluno encontrado." />
    </>
  )
}
