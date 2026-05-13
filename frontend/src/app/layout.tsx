import type { Metadata } from "next";
import "./globals.css";

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
      <body>{children}</body>
    </html>
  );
}
