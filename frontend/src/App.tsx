import type { ReactNode } from 'react'
import { createBrowserRouter, Navigate, Outlet, RouterProvider, useLocation } from 'react-router'
import { LoaderCircle } from 'lucide-react'
import { AppLayout } from '@/components/app-layout'
import { useAuth } from '@/hooks/use-auth'
import { AlunosPage } from '@/pages/alunos'
import { AuditoriaPage } from '@/pages/auditoria'
import { DashboardPage } from '@/pages/dashboard'
import { DisciplinasPage } from '@/pages/disciplinas'
import { EventosPage } from '@/pages/eventos'
import { LoginPage } from '@/pages/login'
import { MatriculasPage } from '@/pages/matriculas'
import { NotFoundPage } from '@/pages/not-found'
import { NotificacoesPage } from '@/pages/notificacoes'

function Carregando() {
  return <div className="flex min-h-svh items-center justify-center"><LoaderCircle className="text-muted-foreground size-6 animate-spin" /></div>
}

// Exige sessão; guarda a rota de origem para voltar depois do login.
function RequerLogin() {
  const { usuario, carregando } = useAuth()
  const { pathname } = useLocation()
  if (carregando) return <Carregando />
  if (!usuario) return <Navigate to="/login" replace state={{ from: pathname }} />
  return <Outlet />
}

function SoAdmin({ children }: { children: ReactNode }) {
  const { usuario } = useAuth()
  if (!usuario?.administrador) return <NotFoundPage titulo="Acesso negado" texto="Esta área é exclusiva do administrador." />
  return children
}

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: <RequerLogin />,
    children: [{
      element: <AppLayout />,
      children: [
        { index: true, element: <DashboardPage /> },
        { path: 'alunos', element: <AlunosPage /> },
        { path: 'disciplinas', element: <DisciplinasPage /> },
        { path: 'matriculas', element: <MatriculasPage /> },
        { path: 'admin/eventos', element: <SoAdmin><EventosPage /></SoAdmin> },
        { path: 'admin/notificacoes', element: <SoAdmin><NotificacoesPage /></SoAdmin> },
        { path: 'admin/auditoria', element: <SoAdmin><AuditoriaPage /></SoAdmin> },
        { path: '*', element: <NotFoundPage /> },
      ],
    }],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
