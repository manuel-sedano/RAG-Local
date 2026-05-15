"use client";

import { FileUp, Loader2 } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatApiError } from "@/lib/api-errors";
import { uploadDocument } from "@/lib/documents-api";
import {
  clientAcceptFileTypes,
  clientAllowedMimeTypes,
  clientMaxUploadBytes,
} from "@/lib/upload-config";
import { cn } from "@/lib/utils";

type Props = {
  kbId: string;
  disabled?: boolean;
  onUploaded: () => void;
};

function validateClientFile(file: File): string | null {
  const max = clientMaxUploadBytes();
  if (file.size > max) {
    return `El archivo supera ${Math.round(max / (1024 * 1024))} MB (límite de interfaz; el servidor también valida).`;
  }
  const allowed = clientAllowedMimeTypes();
  const type = (file.type || "").split(";")[0].trim().toLowerCase();
  if (!type || !allowed.some((m) => m.toLowerCase() === type)) {
    return "Tipo no permitido en esta app. Usa PDF, DOCX o TXT.";
  }
  return null;
}

export function DocumentUploadZone({ kbId, disabled, onUploaded }: Props) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = React.useState(false);
  const [uploading, setUploading] = React.useState(false);
  const [tags, setTags] = React.useState("");
  const [source, setSource] = React.useState("");
  const [language, setLanguage] = React.useState("");

  async function sendFile(file: File) {
    const err = validateClientFile(file);
    if (err) {
      toast.error(err);
      return;
    }
    setUploading(true);
    const tid = toast.loading(`Subiendo «${file.name}»…`);
    try {
      await uploadDocument(kbId, file, { tags, source, language });
      toast.dismiss(tid);
      toast.success("Documento recibido. Aparecerá en la lista con estado UPLOADED.");
      setTags("");
      setSource("");
      setLanguage("");
      onUploaded();
    } catch (e: unknown) {
      toast.dismiss(tid);
      toast.error(formatApiError(e, "No se pudo subir el archivo."));
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  function onPick(ev: React.ChangeEvent<HTMLInputElement>) {
    const f = ev.target.files?.[0];
    if (f) void sendFile(f);
  }

  function onDrop(ev: React.DragEvent) {
    ev.preventDefault();
    setDragOver(false);
    if (disabled || uploading) return;
    const f = ev.dataTransfer.files?.[0];
    if (f) void sendFile(f);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Subir documento</CardTitle>
        <CardDescription>
          Arrastra un archivo o elige uno. Solo UX: el servidor valida MIME, magic bytes y tamaño.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div
          role="button"
          tabIndex={0}
          onKeyDown={(ev) => {
            if (ev.key === "Enter" || ev.key === " ") {
              ev.preventDefault();
              inputRef.current?.click();
            }
          }}
          onDragEnter={(ev) => {
            ev.preventDefault();
            setDragOver(true);
          }}
          onDragOver={(ev) => {
            ev.preventDefault();
            ev.dataTransfer.dropEffect = "copy";
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => !disabled && !uploading && inputRef.current?.click()}
          className={cn(
            "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors",
            dragOver ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-primary/40",
            (disabled || uploading) && "pointer-events-none opacity-60",
          )}
        >
          {uploading ? (
            <Loader2 className="h-10 w-10 animate-spin text-muted-foreground" aria-hidden />
          ) : (
            <FileUp className="h-10 w-10 text-muted-foreground" aria-hidden />
          )}
          <p className="text-sm font-medium">Suelta aquí o haz clic para elegir</p>
          <p className="text-xs text-muted-foreground">PDF, DOCX o TXT · máx. {Math.round(clientMaxUploadBytes() / (1024 * 1024))} MB</p>
          <input
            ref={inputRef}
            type="file"
            className="sr-only"
            accept={clientAcceptFileTypes}
            disabled={disabled || uploading}
            onChange={onPick}
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <div className="grid gap-2">
            <Label htmlFor="doc-tags">Tags (CSV o JSON array)</Label>
            <Input
              id="doc-tags"
              value={tags}
              onChange={(ev) => setTags(ev.target.value)}
              placeholder='p. ej. finanzas, 2025 o ["a","b"]'
              disabled={disabled || uploading}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="doc-source">Origen</Label>
            <Input
              id="doc-source"
              value={source}
              onChange={(ev) => setSource(ev.target.value)}
              placeholder="p. ej. manual interno"
              disabled={disabled || uploading}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="doc-lang">Idioma</Label>
            <Input
              id="doc-lang"
              value={language}
              onChange={(ev) => setLanguage(ev.target.value)}
              placeholder="es"
              maxLength={16}
              disabled={disabled || uploading}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
