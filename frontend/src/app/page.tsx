import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-2xl font-semibold tracking-tight">RAG Local</h1>
      <p className="max-w-md text-center text-muted-foreground">
        Frontend Next.js (App Router) — rama <code className="rounded bg-muted px-1 py-0.5">chore/dev-tooling</code>
      </p>
      <Button type="button">shadcn/ui Button</Button>
    </main>
  );
}
