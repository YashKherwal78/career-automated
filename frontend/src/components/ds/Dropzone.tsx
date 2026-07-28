import * as React from "react";

export interface DsDropzoneProps {
  label?: string;
  hint?: string;
  filetypes?: string[];
  accept?: string;
  onFile?: (file: File) => void;
  className?: string;
}

/**
 * Drag-and-drop file target (Resume Upload / replace-resume modal).
 * Visual idle state matches the handoff; callers own uploading/done/error
 * states above this (see Resume Upload / Career Profile screens).
 */
export function DsDropzone({
  label = "Drop your resume here",
  hint = "or click to browse your files",
  filetypes = ["PDF", "DOCX", "DOC"],
  accept = ".pdf,.doc,.docx",
  onFile,
  className,
}: DsDropzoneProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = React.useState(false);

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0];
    if (file) onFile?.(file);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        handleFiles(e.dataTransfer.files);
      }}
      className={`cursor-pointer text-center bg-[var(--ds-surface-card)] transition-colors ${className ?? ""}`}
      style={{
        border: `2px dashed ${dragOver ? "var(--ds-accent-primary)" : "var(--ds-border-medium)"}`,
        borderRadius: "var(--ds-radius-2xl)",
        padding: "56px 32px",
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <div
        className="mx-auto mb-[22px] flex items-center justify-center"
        style={{
          width: 56,
          height: 56,
          borderRadius: "var(--ds-radius-xl)",
          background: "var(--ds-brand-orange-tint-10)",
        }}
      >
        <div
          style={{
            width: 0,
            height: 0,
            borderLeft: "8px solid transparent",
            borderRight: "8px solid transparent",
            borderBottom: "12px solid var(--ds-accent-primary)",
          }}
        />
      </div>
      <div className="font-[var(--ds-font-display)] font-semibold mb-2" style={{ fontSize: 19 }}>
        {label}
      </div>
      <div className="text-[length:var(--ds-text-md)] text-[var(--ds-text-secondary)] mb-5">
        {hint}
      </div>
      <div className="flex justify-center gap-2">
        {filetypes.map((f) => (
          <span
            key={f}
            className="text-[11.5px] font-semibold text-[var(--ds-text-secondary)] bg-[var(--ds-surface-tint)] px-[11px] py-[5px] rounded-[var(--ds-radius-pill)]"
          >
            {f}
          </span>
        ))}
      </div>
    </div>
  );
}
