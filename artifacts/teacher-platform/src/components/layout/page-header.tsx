import { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
      <div className="px-8 py-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-display font-bold tracking-tight">
              {title}
            </h1>
            {description && (
              <p className="text-sm text-muted-foreground mt-1.5 max-w-2xl">
                {description}
              </p>
            )}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      </div>
    </div>
  );
}
