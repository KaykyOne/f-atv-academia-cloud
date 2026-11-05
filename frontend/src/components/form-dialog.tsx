import { useState, type FormEvent, type ReactNode } from 'react'
import { LoaderCircle, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'

// Modal de cadastro padrão: botão "Novo X" + formulário. Fecha só se salvar com sucesso.
export function FormDialog({ rotulo, titulo, descricao, children, onSubmit, desabilitado }: {
  rotulo: string; titulo: string; descricao: string; children: ReactNode
  onSubmit: (dados: FormData) => Promise<unknown>; desabilitado?: boolean
}) {
  const [aberto, setAberto] = useState(false)
  const [enviando, setEnviando] = useState(false)

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setEnviando(true)
    try { await onSubmit(new FormData(e.currentTarget)); setAberto(false) }
    catch { /* o erro já aparece no toast; o modal continua aberto para corrigir */ }
    finally { setEnviando(false) }
  }

  return (
    <Dialog open={aberto} onOpenChange={setAberto}>
      <DialogTrigger asChild>
        <Button disabled={desabilitado}><Plus />{rotulo}</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={submit} className="grid gap-6">
          <DialogHeader>
            <DialogTitle>{titulo}</DialogTitle>
            <DialogDescription>{descricao}</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4">{children}</div>
          <DialogFooter>
            <DialogClose asChild><Button type="button" variant="outline">Cancelar</Button></DialogClose>
            <Button type="submit" disabled={enviando}>{enviando && <LoaderCircle className="animate-spin" />}Salvar</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
