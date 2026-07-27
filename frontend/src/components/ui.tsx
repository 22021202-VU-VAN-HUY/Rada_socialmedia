import type { ReactNode } from "react";
import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Inbox,
  LoaderCircle,
} from "lucide-react";
import { statusLabel } from "../utils";

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`status-badge status-${status.replaceAll("_", "-")}`}>
      <span className="status-dot" />
      {statusLabel(status)}
    </span>
  );
}

export function LoadingState({ label = "Đang tải dữ liệu" }: { label?: string }) {
  return (
    <div className="state-panel">
      <LoaderCircle className="spin" size={22} />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({
  title,
  detail,
}: {
  title: string;
  detail: string;
}) {
  return (
    <div className="state-panel state-panel-vertical">
      <Inbox size={24} />
      <strong>{title}</strong>
      <span>{detail}</span>
    </div>
  );
}

export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : "Đã xảy ra lỗi.";
  return (
    <div className="inline-alert alert-error">
      <AlertCircle size={18} />
      <span>{message}</span>
    </div>
  );
}

export function Pagination({
  page,
  pages,
  total,
  onPage,
}: {
  page: number;
  pages: number;
  total: number;
  onPage: (page: number) => void;
}) {
  return (
    <div className="pagination">
      <span>{total.toLocaleString("vi-VN")} kết quả</span>
      <div>
        <button
          className="icon-button"
          type="button"
          onClick={() => onPage(page - 1)}
          disabled={page <= 1}
          title="Trang trước"
          aria-label="Trang trước"
        >
          <ChevronLeft size={18} />
        </button>
        <span>
          Trang {page} / {pages}
        </span>
        <button
          className="icon-button"
          type="button"
          onClick={() => onPage(page + 1)}
          disabled={page >= pages}
          title="Trang sau"
          aria-label="Trang sau"
        >
          <ChevronRight size={18} />
        </button>
      </div>
    </div>
  );
}

export function Notice({
  children,
  tone = "info",
}: {
  children: ReactNode;
  tone?: "info" | "success" | "warning";
}) {
  return <div className={`inline-alert alert-${tone}`}>{children}</div>;
}
