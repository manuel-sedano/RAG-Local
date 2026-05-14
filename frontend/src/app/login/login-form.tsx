"use client";

import { isAxiosError, type AxiosError } from "axios";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatApiError } from "@/lib/api-errors";
import { useAuth } from "@/lib/auth-context";

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, ready } = useAuth();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  const expired = searchParams.get("expired") === "1";

  React.useEffect(() => {
    if (expired) {
      toast.warning("Tu sesión expiró o dejó de ser válida. Vuelve a iniciar sesión.", {
        duration: 6000,
      });
    }
  }, [expired]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    const tid = toast.loading("Comprobando credenciales…");
    try {
      await login(email.trim(), password);
      toast.dismiss(tid);
      toast.success("Sesión iniciada correctamente.");
      router.push("/");
      router.refresh();
    } catch (error: unknown) {
      toast.dismiss(tid);
      if (isAxiosError(error)) {
        const axErr = error as AxiosError;
        if (axErr.response?.status === 401) {
          toast.error("Correo o contraseña incorrectos.");
        } else {
          toast.error(formatApiError(axErr, "No se pudo iniciar sesión. Revisa la conexión con el API."));
        }
      } else {
        toast.error(formatApiError(error, "No se pudo iniciar sesión. Revisa la conexión con el API."));
      }
    } finally {
      setLoading(false);
    }
  }

  if (!ready) {
    return (
      <Card className="w-full max-w-[min(100%,24rem)] border-border/60 bg-card/95 shadow-xl backdrop-blur-sm supports-[backdrop-filter]:bg-card/80 dark:border-border/40">
        <CardContent className="flex flex-col items-center gap-3 py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" aria-hidden />
          <p className="text-center text-sm text-muted-foreground">Preparando formulario…</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-[min(100%,24rem)] border-border/60 bg-card/95 shadow-xl backdrop-blur-sm supports-[backdrop-filter]:bg-card/80 dark:border-border/40">
      <CardHeader className="space-y-1 pb-2 text-center sm:text-left">
        <CardTitle className="text-2xl font-semibold tracking-tight">Iniciar sesión</CardTitle>
        <CardDescription className="text-pretty text-base leading-relaxed">
          Introduce tus credenciales del backend RAG Local.
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-2">
        <form className="grid gap-5" onSubmit={onSubmit} noValidate>
          <div className="grid gap-2">
            <Label htmlFor="email" className="text-sm font-medium">
              Correo
            </Label>
            <Input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              inputMode="email"
              required
              value={email}
              onChange={(ev) => setEmail(ev.target.value)}
              placeholder="dev@example.com"
              disabled={loading}
              className="h-11 min-h-[2.75rem] text-base sm:h-10 sm:text-sm"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="password" className="text-sm font-medium">
              Contraseña
            </Label>
            <Input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(ev) => setPassword(ev.target.value)}
              disabled={loading}
              className="h-11 min-h-[2.75rem] text-base sm:h-10 sm:text-sm"
            />
          </div>
          <Button type="submit" disabled={loading} className="h-11 w-full text-base sm:h-10 sm:text-sm">
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                Entrando…
              </>
            ) : (
              "Entrar"
            )}
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            <Link
              href="/"
              className="font-medium text-foreground underline-offset-4 transition-colors hover:text-primary hover:underline"
            >
              Volver al inicio
            </Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
