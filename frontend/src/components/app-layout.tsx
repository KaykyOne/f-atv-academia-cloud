import { useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import {
  Bell, BookOpen, ClipboardList, GraduationCap, LayoutDashboard, LogOut, Menu, Send, Server, ShieldCheck, Users,
  type LucideIcon,
} from 'lucide-react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Separator } from '@/components/ui/separator'
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet'
import { nomePerfil, useAuth } from '@/hooks/use-auth'
import { api, type Resumo } from '@/lib/api'
import { cn } from '@/lib/utils'

interface ItemNav { to: string; label: string; icon: LucideIcon; admin?: boolean }

const secoes: { titulo: string; itens: ItemNav[] }[] = [
  { titulo: 'Acadêmico', itens: [
    { to: '/', label: 'Visão geral', icon: LayoutDashboard },
    { to: '/alunos', label: 'Alunos', icon: Users },
    { to: '/disciplinas', label: 'Disciplinas', icon: BookOpen },
    { to: '/matriculas', label: 'Matrículas', icon: ClipboardList },
  ] },
  { titulo: 'Administração', itens: [
    { to: '/admin/eventos', label: 'Eventos', icon: Send, admin: true },
    { to: '/admin/notificacoes', label: 'Notificações', icon: Bell, admin: true },
    { to: '/admin/auditoria', label: 'Auditoria', icon: ShieldCheck, admin: true },
  ] },
]

const titulos: Record<string, string> = Object.fromEntries(secoes.flatMap((s) => s.itens.map((i) => [i.to, i.label])))

function Navegacao({ onNavigate }: { onNavigate?: () => void }) {
  const { usuario } = useAuth()
  return (
    <nav className="flex flex-col gap-6 px-3">
      {secoes.map((secao) => {
        const itens = secao.itens.filter((i) => !i.admin || usuario?.administrador)
        if (!itens.length) return null
        return (
          <div key={secao.titulo} className="flex flex-col gap-1">
            <span className="text-muted-foreground px-3 pb-1 text-xs font-medium">{secao.titulo}</span>
            {itens.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} end={to === '/'} onClick={onNavigate}
                className={({ isActive }) => cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  isActive ? 'bg-sidebar-accent text-sidebar-accent-foreground' : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground',
                )}>
                <Icon className="size-4" />{label}
              </NavLink>
            ))}
          </div>
        )
      })}
    </nav>
  )
}

function Marca() {
  return (
    <div className="flex items-center gap-2.5 px-6">
      <div className="bg-primary text-primary-foreground flex size-8 items-center justify-center rounded-lg"><GraduationCap className="size-4" /></div>
      <div className="leading-tight">
        <div className="text-sm font-semibold">AcademiaCloud</div>
        <div className="text-muted-foreground text-xs">Docker + Nuvem</div>
      </div>
    </div>
  )
}

function MenuUsuario() {
  const { usuario, sair } = useAuth()
  const navigate = useNavigate()
  if (!usuario) return null
  const iniciais = usuario.nome.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="h-auto gap-2 px-2 py-1.5">
          <Avatar className="size-7"><AvatarFallback className="text-xs">{iniciais}</AvatarFallback></Avatar>
          <div className="hidden text-left leading-tight sm:block">
            <div className="text-sm font-medium">{usuario.nome}</div>
            <div className="text-muted-foreground text-xs">{nomePerfil[usuario.perfil]}</div>
          </div>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-52">
        <DropdownMenuLabel className="font-normal">
          <div className="text-sm font-medium">{usuario.nome}</div>
          <div className="text-muted-foreground text-xs">@{usuario.login} · {nomePerfil[usuario.perfil]}</div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem variant="destructive" onSelect={async () => { await sair(); navigate('/login', { replace: true }) }}>
          <LogOut />Sair
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export function AppLayout() {
  const [menuAberto, setMenuAberto] = useState(false)
  const { pathname } = useLocation()
  // Mostra qual réplica respondeu (demonstração do balanceador - Grupo 4).
  const resumo = useQuery({ queryKey: ['resumo'], queryFn: () => api<Resumo>('resumo'), refetchInterval: 10_000 })

  return (
    <div className="bg-muted/30 flex min-h-svh">
      <aside className="bg-sidebar border-sidebar-border sticky top-0 hidden h-svh w-64 shrink-0 flex-col gap-6 border-r py-5 md:flex">
        <Marca />
        <Separator />
        <Navegacao />
        <div className="text-muted-foreground mt-auto px-6 text-xs">Base didática · use somente dados fictícios.</div>
      </aside>

      <Sheet open={menuAberto} onOpenChange={setMenuAberto}>
        <SheetContent side="left" className="w-64 gap-6 py-5">
          <SheetTitle className="sr-only">Menu</SheetTitle>
          <SheetDescription className="sr-only">Navegação do sistema</SheetDescription>
          <Marca />
          <Separator />
          <Navegacao onNavigate={() => setMenuAberto(false)} />
        </SheetContent>
      </Sheet>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="bg-background/80 sticky top-0 z-30 flex h-14 items-center gap-3 border-b px-4 backdrop-blur md:px-6">
          <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setMenuAberto(true)} aria-label="Abrir menu"><Menu /></Button>
          <span className="text-sm font-medium">{titulos[pathname] ?? 'AcademiaCloud'}</span>
          <div className="ml-auto flex items-center gap-3">
            {resumo.data && (
              <Badge variant="outline" className="text-muted-foreground hidden gap-1.5 font-mono sm:inline-flex" title="Réplica web que respondeu">
                <Server />{resumo.data.instancia}
              </Badge>
            )}
            <MenuUsuario />
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 space-y-6 p-4 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
