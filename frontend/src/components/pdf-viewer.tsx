"use client";

import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/page-state";
import { es } from "@/lib/i18n/es";

type PdfDoc = {
  numPages: number;
  getPage: (n: number) => Promise<{
    getViewport: (opts: { scale: number }) => { width: number; height: number };
    render: (ctx: { canvasContext: CanvasRenderingContext2D; viewport: { width: number; height: number } }) => {
      promise: Promise<void>;
    };
  }>;
};

type Props = {
  data: ArrayBuffer;
  page: number;
  onPageChange?: (page: number) => void;
};

export function PdfViewer({ data, page, onPageChange }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [pdf, setPdf] = useState<PdfDoc | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(Math.max(1, page));

  /* eslint-disable react-hooks/set-state-in-effect -- visor PDF: sync página y carga */
  useEffect(() => {
    setCurrentPage(Math.max(1, page));
  }, [page]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void (async () => {
      try {
        const pdfjs = await import("pdfjs-dist");
        pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
        const task = pdfjs.getDocument({ data: data.slice(0) });
        const doc = await task.promise;
        if (!cancelled) setPdf(doc as unknown as PdfDoc);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : es.documents.viewerPdfError);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [data]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const renderPage = useCallback(
    async (pageNum: number) => {
      if (!pdf || !canvasRef.current) return;
      const p = await pdf.getPage(pageNum);
      const viewport = p.getViewport({ scale: 1.25 });
      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      canvas.height = viewport.height;
      canvas.width = viewport.width;
      await p.render({ canvasContext: ctx, viewport }).promise;
    },
    [pdf],
  );

  useEffect(() => {
    if (!pdf) return;
    const n = Math.min(Math.max(1, currentPage), pdf.numPages);
    void renderPage(n);
  }, [pdf, currentPage, renderPage]);

  function goTo(next: number) {
    if (!pdf) return;
    const n = Math.min(Math.max(1, next), pdf.numPages);
    setCurrentPage(n);
    onPageChange?.(n);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
        <Loader2 className="h-6 w-6 animate-spin" aria-hidden />
        {es.documents.loadingViewer}
      </div>
    );
  }

  if (error) {
    return <ErrorState message={error} />;
  }

  if (!pdf) return null;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          {es.documents.pageOf} {currentPage} / {pdf.numPages}
        </p>
        <div className="flex gap-1">
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={currentPage <= 1}
            onClick={() => goTo(currentPage - 1)}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={currentPage >= pdf.numPages}
            onClick={() => goTo(currentPage + 1)}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <div className="overflow-auto rounded-md border bg-muted/20 p-2">
        <canvas ref={canvasRef} className="mx-auto max-w-full" />
      </div>
    </div>
  );
}
