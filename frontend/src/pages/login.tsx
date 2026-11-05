import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router'
import { GraduationCap, LoaderCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuth } from '@/hooks/use-auth'

export function LoginPage() {
  const { usuario, entrar } = useAuth()
  const navigate = useNavigate()
  const destino = (useLocation().state as { from?: string } | null)?.from ?? '/'
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  if (usuario) return <Navigate to={destino} replace />

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const f = new FormData(e.currentTarget)
    setErro(null); setEnviando(true)
    try {
      await entrar(String(f.get('usuario')), String(f.get('senha')))
      navigate(destino, { replace: true })
    } catch (err) {
      setErro((err as Error).message)
    } finally { setEnviando(false) }
  }

  return (
    <div className="bg-muted/40 flex min-h-svh flex-col items-center justify-center gap-6 p-6">
      <div className="flex items-center gap-2.5">
        <div className="bg-primary text-primary-foreground flex size-9 items-center justify-center rounded-lg"><GraduationCap className="size-5" /></div>
        <span className="text-lg font-semibold">AcademiaCloud</span>
      </div>
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-xl">Entrar</CardTitle>
          <CardDescription>Acesse com seu usuário institucional</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="grid gap-5">
            <div className="grid gap-2">
              <Label htmlFor="usuario">Usuário</Label>
              <Input id="usuario" name="usuario" autoComplete="username" placeholder="admin, secretaria ou professor" required maxLength={40} autoFocus />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="senha">Senha</Label>
              <Input id="senha" name="senha" type="password" autoComplete="current-password" required aria-invalid={!!erro} />
            </div>
            {erro && <p role="alert" className="text-destructive text-sm">{erro}</p>}
            <Button type="submit" className="w-full" disabled={enviando}>
              {enviando && <LoaderCircle className="animate-spin" />}Entrar
            </Button>
          </form>
        </CardContent>
      </Card>
      <p className="text-muted-foreground max-w-sm text-center text-xs">Ambiente didático. As senhas iniciais estão no arquivo <code>.env</code>. Use somente dados fictícios.</p>
    </div>
  )
}
