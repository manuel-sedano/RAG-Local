"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MIME_FILTER_OPTIONS, STATUS_FILTER_OPTIONS } from "@/lib/document-mime";
import { es } from "@/lib/i18n/es";

export type DocumentFilterState = {
  status: string;
  mimeType: string;
  tagsQuery: string;
  sourceQuery: string;
};

type Props = {
  value: DocumentFilterState;
  onChange: (next: DocumentFilterState) => void;
};

export function DocumentFilters({ value, onChange }: Props) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <FilterField label={es.documents.filterStatus} id="filter-status">
        <select
          id="filter-status"
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm"
          value={value.status}
          onChange={(ev) => onChange({ ...value, status: ev.target.value })}
        >
          {STATUS_FILTER_OPTIONS.map((o) => (
            <option key={o.value || "all"} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </FilterField>
      <FilterField label={es.documents.filterType} id="filter-mime">
        <select
          id="filter-mime"
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm"
          value={value.mimeType}
          onChange={(ev) => onChange({ ...value, mimeType: ev.target.value })}
        >
          {MIME_FILTER_OPTIONS.map((o) => (
            <option key={o.value || "all"} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </FilterField>
      <FilterField label={es.documents.filterTags} id="filter-tags">
        <Input
          id="filter-tags"
          value={value.tagsQuery}
          onChange={(ev) => onChange({ ...value, tagsQuery: ev.target.value })}
          placeholder={es.documents.filterTagsPlaceholder}
        />
      </FilterField>
      <FilterField label={es.documents.filterSource} id="filter-source">
        <Input
          id="filter-source"
          value={value.sourceQuery}
          onChange={(ev) => onChange({ ...value, sourceQuery: ev.target.value })}
          placeholder={es.documents.filterSourcePlaceholder}
        />
      </FilterField>
    </div>
  );
}

function FilterField({
  label,
  id,
  children,
}: {
  label: string;
  id: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={id} className="text-xs text-muted-foreground">
        {label}
      </Label>
      {children}
    </div>
  );
}
