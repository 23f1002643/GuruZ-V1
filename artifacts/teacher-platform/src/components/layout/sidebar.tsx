import { Link, useLocation } from 'wouter';
import { useTheme } from '@/components/theme-provider';
import { useHealthCheck } from '@workspace/api-client-react';
import {
  LayoutDashboard,
  Upload,
  ListChecks,
  Package,
  FileText,
  Settings,
  Moon,
  Sun,
  Activity,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/upload', label: 'Upload', icon: Upload },
  { path: '/jobs', label: 'Jobs', icon: ListChecks },
  { path: '/packages', label: 'Packages', icon: Package },
  { path: '/logs', label: 'Logs', icon: FileText },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const [location] = useLocation();
  const { theme, setTheme } = useTheme();
  const { data: health } = useHealthCheck();

  return (
    <aside className="w-64 border-r border-border bg-card flex flex-col h-screen sticky top-0">
      <div className="p-6 border-b border-border">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-display font-bold tracking-tight">
              AI Teacher
            </h1>
            <p className="text-xs text-muted-foreground font-mono mt-0.5">
              PLATFORM v1.0
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            data-testid="button-theme-toggle"
            className="h-8 w-8"
          >
            {theme === 'dark' ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </Button>
        </div>
        
        <div className="mt-4 flex items-center gap-2">
          <div
            className={cn(
              'h-2 w-2 rounded-full',
              health?.status === 'healthy'
                ? 'bg-emerald-500 animate-pulse'
                : 'bg-red-500'
            )}
            data-testid="indicator-health-status"
          />
          <span className="text-xs font-mono text-muted-foreground uppercase tracking-wide">
            {health?.status === 'healthy' ? 'Online' : 'Offline'}
          </span>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = location === item.path;
          
          return (
            <Link
              key={item.path}
              href={item.path}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              )}
              data-testid={`nav-${item.label.toLowerCase()}`}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono">
          <Activity className="h-3 w-3" />
          <span>System Active</span>
        </div>
      </div>
    </aside>
  );
}
