"use client";

import { usePathname } from "next/navigation";

import { AppHeader } from "@/components/app-header";
import { useAuth } from "@/lib/auth-context";
import { useKbRouteSync } from "@/hooks/use-kb-route-sync";

export function AuthenticatedChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, ready } = useAuth();
  useKbRouteSync();

  const isLogin = pathname.startsWith("/login");
  const showChrome = ready && user && !isLogin;

  if (!showChrome) {
    return <>{children}</>;
  }

  return (
    <>
      <AppHeader />
      {children}
    </>
  );
}
