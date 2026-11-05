import { Link } from 'react-router'
import { Button } from '@/components/ui/button'

export function NotFoundPage({ titulo = 'Página não encontrada', texto = 'O endereço acessado não existe.' }: { titulo?: string; texto?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-24 text-center">
      <h1 className="text-2xl font-semibold">{titulo}</h1>
      <p className="text-muted-foreground text-sm">{texto}</p>
      <Button asChild variant="outline"><Link to="/">Voltar ao início</Link></Button>
    </div>
  )
}
