"use client";

import { FileUp, Loader2 } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useIngestProgress } from "@/hooks/use-ingest-progress";
import { formatApiError } from "@/lib/api-errors";
import { uploadDocument } from "@/lib/documents-api";
import { es } from "@/lib/i18n/es";
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
    return es.documents.uploadTooLarge.replace("{mb}", String(Math.round(max / (1024 * 1024))));
  }
  const allowed = clientAllowedMimeTypes();
  const type = (file.type || "").split(";")[0].trim().toLowerCase();
  if (!type || !allowed.some((m) => m.toLowerCase() === type)) {
    return es.documents.uploadInvalidType;
  }
  return null;
}

export function DocumentUploadZone({ kbId, disabled, onUploaded }: Props) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = React.useState(false);
  const [uploading, setUploading] = React.useState(false);
  const [trackingDocId, setTrackingDocId] = React.useState<string | null>(null);
  const [tags, setTags] = React.useState("");
  const [source, setSource] = React.useState("");
  const [language, setLanguage] = React.useState("");

  const ingestProgress = useIngestProgress(trackingDocId);

  React.useEffect(() => {
    if (!ingestProgress || ingestProgress.percent < 100) return;
    const t = window.setTimeout(() => setTrackingDocId(null), 3000);
    return () => window.clearTimeout(t);
  }, [ingestProgress]);

  async function sendFile(file: File) {
    const err = validateClientFile(file);
    if (err) {
      toast.error(err);
      return;
    }
    setUploading(true);
    const tid = toast.loading(es.documents.uploading.replace("{name}", file.name));
    try {
      const res = await uploadDocument(kbId, file, { tags, source, language });
      toast.dismiss(tid);
      toast.success(es.documents.uploadOk);
      setTrackingDocId(res.document_id);
      setTags("");
      setSource("");
      setLanguage("");
      onUploaded();
    } catch (e: unknown) {
      toast.dismiss(tid);
      toast.error(formatApiError(e, es.documents.uploadError));
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
        <CardTitle className="text-lg">{es.documents.uploadSection}</CardTitle>
        <CardDescription>{es.documents.uploadHint}</CardDescription>
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
          <p className="text-sm font-medium">{es.documents.uploadDrop}</p>
          <p className="text-xs text-muted-foreground">
            {es.documents.uploadFormats.replace(
              "{mb}",
              String(Math.round(clientMaxUploadBytes() / (1024 * 1024))),
            )}
          </p>
          <input
            ref={inputRef}
            type="file"
            className="sr-only"
            accept={clientAcceptFileTypes}
            disabled={disabled || uploading}
            onChange={onPick}
          />
        </div>

        {ingestProgress ? (
          <div className="rounded-md border bg-muted/30 px-3 py-2 text-sm">
            <div className="mb-1 flex justify-between text-xs text-muted-foreground">
              <span>
                {es.documents.ingestLive}: <strong>{ingestProgress.stage}</strong>
              </span>
              <span>{ingestProgress.percent}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full bg-primary transition-all duration-300"
                style={{ width: `${ingestProgress.percent}%` }}
              />
            </div>
          </div>
        ) : null}

        <div className="grid gap-3 sm:grid-cols-3">
          <div className="grid gap-2">
            <Label htmlFor="doc-tags">{es.documents.tagsLabel}</Label>
            <Input
              id="doc-tags"
              value={tags}
              onChange={(ev) => setTags(ev.target.value)}
              placeholder={es.documents.tagsPlaceholder}
              disabled={disabled || uploading}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="doc-source">{es.documents.sourceLabel}</Label>
            <Input
              id="doc-source"
              value={source}
              onChange={(ev) => setSource(ev.target.value)}
              placeholder={es.documents.sourcePlaceholder}
              disabled={disabled || uploading}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="doc-lang">{es.documents.langLabel}</Label>
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
