'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import {
  Activity, MessageSquare, FileText, LayoutDashboard, User,
  LogOut, Moon, Sun, Bell, Shield, ChevronLeft, ChevronRight, Menu
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { useI18n } from '@/i18n/context';
import { LanguageSelector } from '@/components/layout/LanguageSelector';
import toast from 'react-hot-toast';
import { cn } from '@/lib/utils';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout, fetchProfile, isAuthenticated } = useAuthStore();
  const { theme, setTheme } = useTheme();
  const { t } = useI18n();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    if (!isAuthenticated) { router.push('/auth/login'); return; }
    if (!user) fetchProfile();
  }, [isAuthenticated]);

  const navItems = [
    { href: '/dashboard', icon: LayoutDashboard, label: t('nav.dashboard') },
    { href: '/chat', icon: MessageSquare, label: t('nav.chat') },
    { href: '/documents', icon: FileText, label: t('nav.documents') },
    { href: '/profile', icon: User, label: t('nav.profile') },
  ];

  const adminItems = [
    { href: '/admin', icon: Shield, label: t('nav.admin') },
  ];

  const handleLogout = async () => {
    await logout();
    toast.success(t('auth.logoutSuccess'));
    router.push('/auth/login');
  };

  const NavLink = ({ item }: { item: { href: string; icon: any; label: string } }) => {
    const active = pathname === item.href || pathname.startsWith(item.href + '/');
    return (
      <Link href={item.href} onClick={() => setMobileOpen(false)}
        className={cn('flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all',
          active ? 'bg-primary text-white shadow-sm' : 'text-muted-foreground hover:bg-muted hover:text-foreground',
          collapsed && 'justify-center px-2'
        )}>
        <item.icon className="w-5 h-5 flex-shrink-0" />
        {!collapsed && <span>{item.label}</span>}
      </Link>
    );
  };

  const Sidebar = () => (
    <div className={cn('flex flex-col h-full bg-card border-r transition-all duration-300', collapsed ? 'w-16' : 'w-60')}>
      {/* Logo */}
      <div className={cn('flex items-center gap-2 p-4 border-b', collapsed && 'justify-center')}>
        <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center flex-shrink-0">
          <Activity className="w-5 h-5 text-white" />
        </div>
        {!collapsed && <span className="font-bold text-lg">MedicalRAG</span>}
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => <NavLink key={item.href} item={item} />)}
        {user?.role === 'admin' && (
          <>
            <div className={cn('my-3 border-t', collapsed && 'mx-2')} />
            {adminItems.map((item) => <NavLink key={item.href} item={item} />)}
          </>
        )}
      </nav>

      {/* Bottom actions */}
      <div className="p-3 border-t space-y-1">
        {mounted && (
          <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className={cn('flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-muted-foreground hover:bg-muted w-full transition-all', collapsed && 'justify-center px-2')}>
            {theme === 'dark' ? <Sun className="w-5 h-5 flex-shrink-0" /> : <Moon className="w-5 h-5 flex-shrink-0" />}
            {!collapsed && <span>{theme === 'dark' ? t('nav.lightMode') : t('nav.darkMode')}</span>}
          </button>
        )}
        <button onClick={handleLogout}
          className={cn('flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-destructive hover:bg-destructive/10 w-full transition-all', collapsed && 'justify-center px-2')}>
          <LogOut className="w-5 h-5 flex-shrink-0" />
          {!collapsed && <span>{t('nav.logout')}</span>}
        </button>
        {!collapsed && user && (
          <div className="flex items-center gap-3 px-3 py-2 mt-1">
            <div className="w-8 h-8 bg-primary/20 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-primary font-semibold text-xs">{user.username?.[0]?.toUpperCase()}</span>
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{user.full_name || user.username}</p>
              <p className="text-xs text-muted-foreground capitalize">{user.role}</p>
            </div>
          </div>
        )}
      </div>

      {/* Collapse toggle - desktop only */}
      <button onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-20 w-6 h-6 bg-card border rounded-full items-center justify-center shadow-sm hover:bg-muted transition-colors hidden lg:flex z-10">
        {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
      </button>
    </div>
  );

  if (!isAuthenticated) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full" />
    </div>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-background relative">
      {/* Desktop Sidebar */}
      <div className="hidden lg:flex relative flex-shrink-0">
        <Sidebar />
      </div>

      {/* Mobile Sidebar overlay */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div className="fixed inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
          <div className="relative flex w-60 flex-shrink-0">
            <Sidebar />
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Top bar */}
        <header className="h-14 border-b bg-card flex items-center justify-between px-4 flex-shrink-0">
          <button onClick={() => setMobileOpen(true)} className="lg:hidden p-2 rounded-lg hover:bg-muted">
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex-1" />
          <div className="flex items-center gap-2">
            <LanguageSelector />
            <Link href="/profile" className="p-2 rounded-lg hover:bg-muted">
              <Bell className="w-5 h-5 text-muted-foreground" />
            </Link>
            {user && (
              <div className="w-8 h-8 bg-primary/20 rounded-full flex items-center justify-center cursor-pointer">
                <span className="text-primary font-semibold text-xs">{user.username?.[0]?.toUpperCase()}</span>
              </div>
            )}
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
