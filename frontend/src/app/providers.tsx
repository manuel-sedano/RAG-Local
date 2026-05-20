"use client";

import { Toaster } from "sonner";

import { AuthenticatedChrome } from "@/components/authenticated-chrome";
import { AuthProvider } from "@/lib/auth-context";
import { KnowledgeBasesProvider } from "@/lib/kb-context";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <KnowledgeBasesProvider>
        <AuthenticatedChrome>{children}</AuthenticatedChrome>
        <Toaster richColors closeButton position="top-center" />
      </KnowledgeBasesProvider>
    </AuthProvider>
  );
}
