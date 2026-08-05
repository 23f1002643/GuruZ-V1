import { Link } from 'wouter';
import { Button } from '@/components/ui/button';
import { Home } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center space-y-4">
        <div className="text-8xl font-display font-bold text-muted-foreground/30">404</div>
        <h1 className="text-2xl font-display font-bold">Page Not Found</h1>
        <p className="text-muted-foreground max-w-sm">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <Link href="/">
          <Button className="mt-2">
            <Home className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Button>
        </Link>
      </div>
    </div>
  );
}
