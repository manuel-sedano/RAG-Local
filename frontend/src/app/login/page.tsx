import { Loader2 } from "lucide-react";
import { Suspense } from "react";

import { LoginForm } from "@/app/login/login-form";

function LoginFallback() {
  return (
    <div
      className="flex w-full max-w-[min(100%,24rem)] flex-col items-center gap-3 rounded-xl border border-border/60 bg-card/95 px-6 py-12 shadow-xl backdrop-blur-sm dark:border-border/40"
      role="status"
      aria-live="polite"
    >
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" aria-hidden />
      <p className="text-center text-sm text-muted-foreground">Cargando…</p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <main className="relative flex min-h-[100dvh] flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-neutral-50 via-neutral-100 to-neutral-200 px-4 py-10 dark:from-neutral-950 dark:via-neutral-900 dark:to-neutral-950 sm:px-6">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,hsl(var(--primary)/0.12),transparent)] dark:bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,hsl(var(--primary)/0.18),transparent)]"
        aria-hidden
      />
      <div className="relative z-10 w-full max-w-lg">
        <Suspense fallback={<LoginFallback />}>
          <LoginForm />
        </Suspense>
      </div>
    </main>
  );
}
