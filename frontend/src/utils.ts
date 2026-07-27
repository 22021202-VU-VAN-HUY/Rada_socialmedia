export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

export function relativeTime(
  value: string | null,
  fallback: string | null = null,
): string {
  if (!value) return fallback || "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return fallback || "—";
  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (seconds < 60) return "Vừa xong";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} phút`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} giờ`;
  return `${Math.floor(hours / 24)} ngày`;
}

export function startForRange(range: string): string | undefined {
  if (range === "all") return undefined;
  const now = new Date();
  if (range === "today") {
    now.setHours(0, 0, 0, 0);
  } else {
    now.setDate(now.getDate() - Number(range));
  }
  return now.toISOString();
}

export function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    queued: "Đang chờ",
    running: "Đang lấy dữ liệu",
    completed: "Hoàn tất",
    failed: "Thất bại",
    connected: "Đã kết nối",
    disconnected: "Chưa kết nối",
    pending_login: "Chờ đăng nhập",
    pending_authorization: "Chờ cấp quyền",
    reauth_required: "Cần đăng nhập lại",
    error: "Có lỗi",
    never: "Chưa chạy",
    deleted: "Đã xóa",
  };
  return labels[status] || status;
}
