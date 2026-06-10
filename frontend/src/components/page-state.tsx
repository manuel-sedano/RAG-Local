"use client";

import { AlertCircle, Inbox, Loader2 } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { es } from "@/lib/i18n/es";
import { cn } from "@/lib/utils";

type BaseProps = {
  className?: string;
};

export function LoadingState({
  message = es.states.loading,
  className,
  fullPage = false,
}: BaseProps & { message?: string; fullPage?: boolean }) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 text-sm text-muted-foreground",
        fullPage ? "min-h-[50vh]" : "py-12",
        className,
      )}
      role="status"
      aria-live="polite"
    >
      <Loader2 className="h-8 w-8 animate-spin" aria-hidden />
      <span>{message}</span>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  className,
}: BaseProps & {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed px-6 py-10 text-center",
        className,
      )}
    >
      <Inbox className="h-10 w-10 text-muted-foreground/60" aria-hidden />
      <div className="space-y-1">
        <p className="font-medium text-foreground">{title}</p>
        {description ? <p className="max-w-sm text-sm text-muted-foreground">{description}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function ErrorState({
  title,
  message,
  onRetry,
  className,
}: BaseProps & {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-6 py-8 text-center",
        className,
      )}
      role="alert"
    >
      <AlertCircle className="h-9 w-9 text-destructive" aria-hidden />
      <div className="space-y-1">
        {title ? <p className="font-medium text-destructive">{title}</p> : null}
        <p className="max-w-md text-sm text-destructive/90">{message}</p>
      </div>
      {onRetry ? (
        <Button type="button" variant="outline" size="sm" onClick={onRetry}>
          {es.states.retry}
        </Button>
      ) : null}
    </div>
  );
}
