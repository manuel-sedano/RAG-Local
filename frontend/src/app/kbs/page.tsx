"use client";

import { Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatApiError } from "@/lib/api-errors";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { useKnowledgeBases } from "@/lib/kb-context";
import type { KnowledgeBaseDto } from "@/lib/kb-context";

export default function KnowledgeBasesPage() {
  const router = useRouter();
  const { user, ready } = useAuth();
  const { items, loading, reload, activeKbId, setActiveKbId } = useKnowledgeBases();

  const [createName, setCreateName] = React.useState("");
  const [createDesc, setCreateDesc] = React.useState("");
  const [creating, setCreating] = React.useState(false);

  const [editing, setEditing] = React.useState<KnowledgeBaseDto | null>(null);
  const [editName, setEditName] = React.useState("");
  const [editDesc, setEditDesc] = React.useState("");
  const [savingEdit, setSavingEdit] = React.useState(false);

  React.useEffect(() => {
    if (ready && !user) {
      router.replace("/login");
    }
  }, [ready, user, router]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!createName.trim()) {
      toast.error("El nombre es obligatorio.");
      return;
    }
    setCreating(true);
    const tid = toast.loading("Creando base de conocimiento…");
    try {
      await api.post("/api/kbs", {
        name: createName.trim(),
        description: createDesc.trim() || null,
      });
      toast.dismiss(tid);
      toast.success("Base creada correctamente.");
      setCreateName("");
      setCreateDesc("");
      await reload();
    } catch (error: unknown) {
      toast.dismiss(tid);
      toast.error(formatApiError(error, "No se pudo crear la base."));
    } finally {
      setCreating(false);
    }
  }

  function startEdit(kb: KnowledgeBaseDto) {
    setEditing(kb);
    setEditName(kb.name);
    setEditDesc(kb.description ?? "");
  }

  async function saveEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editing) return;
    if (!editName.trim()) {
      toast.error("El nombre no puede quedar vacío.");
      return;
    }
    setSavingEdit(true);
    const tid = toast.loading("Guardando cambios…");
    try {
      const payload: { name: string; description?: string | null } = { name: editName.trim() };
      if (editDesc.trim() === "") {
        payload.description = null;
      } else {
        payload.description = editDesc.trim();
      }
      await api.patch(`/api/kbs/${editing.id}`, payload);
      toast.dismiss(tid);
      toast.success("Cambios guardados.");
      setEditing(null);
      await reload();
    } catch (error: unknown) {
      toast.dismiss(tid);
      toast.error(formatApiError(error, "No se pudo guardar."));
    } finally {
      setSavingEdit(false);
    }
  }

  async function onDelete(kb: KnowledgeBaseDto) {
    const ok = window.confirm(
      `¿Eliminar la base «${kb.name}»? Los documentos asociados quedarán inaccesibles desde esta interfaz.`,
    );
    if (!ok) return;
    const tid = toast.loading("Eliminando…");
    try {
      await api.delete(`/api/kbs/${kb.id}`);
      toast.dismiss(tid);
      toast.success("Base eliminada.");
      if (activeKbId === kb.id) setActiveKbId(null);
      await reload();
    } catch (error: unknown) {
      toast.dismiss(tid);
      toast.error(formatApiError(error, "No se pudo eliminar."));
    }
  }

  if (!ready || !user) {
    return (
      <main className="flex min-h-[100dvh] items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" aria-hidden />
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-[100dvh] max-w-3xl flex-col gap-8 p-6 pb-16">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Bases de conocimiento</h1>
          <p className="text-sm text-muted-foreground">Crea, edita y elige la KB activa para el resto de la app.</p>
        </div>
        <Button variant="outline" asChild>
          <Link href="/">Volver al inicio</Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Nueva base</CardTitle>
          <CardDescription>Nombre obligatorio; descripción opcional.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4" onSubmit={onCreate}>
            <div className="grid gap-2">
              <Label htmlFor="kb-name">Nombre</Label>
              <Input
                id="kb-name"
                value={createName}
                onChange={(ev) => setCreateName(ev.target.value)}
                placeholder="p. ej. Finanzas internas"
                disabled={creating}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="kb-desc">Descripción</Label>
              <textarea
                id="kb-desc"
                value={createDesc}
                onChange={(ev) => setCreateDesc(ev.target.value)}
                placeholder="Opcional"
                disabled={creating}
                rows={3}
                className="flex min-h-[72px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>
            <Button type="submit" disabled={creating} className="w-fit gap-2">
              {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Crear
            </Button>
          </form>
        </CardContent>
      </Card>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Tus bases</h2>
        {loading ? (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            Cargando…
          </p>
        ) : items.length === 0 ? (
          <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
            Aún no tienes bases. Crea una arriba para empezar a subir documentos cuando el pipeline esté listo.
          </p>
        ) : (
          <ul className="flex flex-col gap-3">
            {items.map((kb) => (
              <li key={kb.id}>
                <Card className={activeKbId === kb.id ? "border-primary/60 ring-1 ring-primary/20" : ""}>
                  <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3 space-y-0 pb-2">
                    <div className="space-y-1">
                      <CardTitle className="text-base">{kb.name}</CardTitle>
                      {kb.description ? (
                        <CardDescription className="text-pretty">{kb.description}</CardDescription>
                      ) : (
                        <CardDescription className="italic">Sin descripción</CardDescription>
                      )}
                      <p className="text-xs text-muted-foreground">
                        Actualizada: {new Date(kb.updated_at).toLocaleString("es")}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        type="button"
                        size="sm"
                        variant={activeKbId === kb.id ? "default" : "secondary"}
                        onClick={() => setActiveKbId(kb.id)}
                      >
                        {activeKbId === kb.id ? "Activa" : "Usar como activa"}
                      </Button>
                      <Button type="button" size="sm" variant="outline" onClick={() => startEdit(kb)}>
                        <Pencil className="h-3.5 w-3.5" />
                        Editar
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="destructive"
                        className="gap-1"
                        onClick={() => void onDelete(kb)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Eliminar
                      </Button>
                    </div>
                  </CardHeader>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>

      {editing ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center" role="dialog">
          <Card className="w-full max-w-lg shadow-lg">
            <CardHeader>
              <CardTitle>Editar base</CardTitle>
              <CardDescription>Los cambios se guardan en el servidor.</CardDescription>
            </CardHeader>
            <CardContent>
              <form className="grid gap-4" onSubmit={saveEdit}>
                <div className="grid gap-2">
                  <Label htmlFor="edit-name">Nombre</Label>
                  <Input
                    id="edit-name"
                    value={editName}
                    onChange={(ev) => setEditName(ev.target.value)}
                    disabled={savingEdit}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="edit-desc">Descripción</Label>
                  <textarea
                    id="edit-desc"
                    value={editDesc}
                    onChange={(ev) => setEditDesc(ev.target.value)}
                    rows={3}
                    disabled={savingEdit}
                    className="flex min-h-[72px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                  />
                  <p className="text-xs text-muted-foreground">Deja la descripción vacía para borrarla.</p>
                </div>
                <div className="flex flex-wrap justify-end gap-2">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => setEditing(null)}
                    disabled={savingEdit}
                  >
                    Cancelar
                  </Button>
                  <Button type="submit" disabled={savingEdit} className="gap-2">
                    {savingEdit ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                    Guardar
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </main>
  );
}
