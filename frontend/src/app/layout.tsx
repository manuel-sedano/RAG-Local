import type { Metadata } from "next";
import "./globals.css";

import { Providers } from "@/app/providers";

export const metadata: Metadata = {
  title: "RAG Local",
  description: "Plataforma RAG local — frontend dev tooling",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
