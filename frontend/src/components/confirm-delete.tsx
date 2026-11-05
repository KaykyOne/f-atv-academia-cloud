import { Trash2 } from 'lucide-react'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Button, buttonVariants } from '@/components/ui/button'

export function ConfirmDelete({ titulo, descricao, onConfirm, disabled }: {
  titulo: string; descricao: string; onConfirm: () => void; disabled?: boolean
}) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-destructive size-8" disabled={disabled} aria-label={titulo}>
          <Trash2 />
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{titulo}</AlertDialogTitle>
          <AlertDialogDescription>{descricao}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancelar</AlertDialogCancel>
          <AlertDialogAction className={buttonVariants({ variant: 'destructive' })} onClick={onConfirm}>Excluir</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
