"use client";

import { Toaster } from "sonner";

import { AuthProvider } from "@/lib/auth-context";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      {children}
      <Toaster richColors closeButton position="top-center" />
    </AuthProvider>
  );
}
