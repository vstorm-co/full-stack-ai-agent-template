import Link from "next/link";

export default function NotFound() {
  return (
    <div className="bg-background flex min-h-screen flex-col items-center justify-center px-4 text-center">
      <p className="text-brand text-sm font-semibold tracking-wider uppercase">404</p>
      <h1 className="text-foreground mt-2 text-4xl font-bold tracking-tight sm:text-5xl">
        Page not found
      </h1>
      <p className="text-muted-foreground mt-4">
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
      </p>
      <div className="mt-8 flex gap-3">
        <Link
          href="/"
          className="bg-brand text-brand-foreground hover:bg-brand/90 inline-flex items-center rounded-lg px-4 py-2.5 text-sm font-medium transition-colors"
        >
          Go home
        </Link>
        <Link
          href="/dashboard"
          className="bg-secondary text-secondary-foreground hover:bg-secondary/80 inline-flex items-center rounded-lg px-4 py-2.5 text-sm font-medium transition-colors"
        >
          Dashboard
        </Link>
      </div>
    </div>
  );
}
