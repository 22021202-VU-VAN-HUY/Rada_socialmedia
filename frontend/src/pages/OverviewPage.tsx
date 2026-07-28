import { useQuery } from "@tanstack/react-query";
import {
  CalendarClock,
  Link2,
  MessageSquareText,
  Newspaper,
  Radio,
} from "lucide-react";
import { api } from "../api";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  StatusBadge,
} from "../components/ui";
import { useJobs } from "../hooks/useJobs";
import { formatDateTime } from "../utils";

export function OverviewPage() {
  const overview = useQuery({ queryKey: ["overview"], queryFn: api.overview });
  const jobs = useJobs();

  return (
    <>
      <PageHeader
        title="Tổng quan"
        description="Tình hình kết nối và thu thập dữ liệu mạng xã hội."
      />
      {overview.isLoading ? (
        <LoadingState />
      ) : overview.error ? (
        <ErrorState error={overview.error} />
      ) : (
        <div className="metric-grid">
          <Metric
            label="Bài viết"
            value={overview.data?.posts || 0}
            icon={<Newspaper size={20} />}
            tone="green"
          />
          <Metric
            label="Bình luận"
            value={overview.data?.comments || 0}
            icon={<MessageSquareText size={20} />}
            tone="blue"
          />
          <Metric
            label="Cấu hình đã lưu"
            value={overview.data?.saved_configurations || 0}
            icon={<CalendarClock size={20} />}
            tone="amber"
          />
          <Metric
            label="Nền tảng kết nối"
            value={overview.data?.connected_platforms || 0}
            icon={<Link2 size={20} />}
            tone="red"
          />
        </div>
      )}

      <section className="content-section">
        <div className="section-heading">
          <div>
            <h2>Hoạt động gần đây</h2>
            <p>Các lượt thu thập được tạo từ tài khoản này.</p>
          </div>
          {jobs.activeJob && (
            <span className="live-indicator">
              <Radio size={15} /> Đang cập nhật
            </span>
          )}
        </div>
        {jobs.isLoading ? (
          <LoadingState label="Đang tải hoạt động" />
        ) : jobs.error ? (
          <ErrorState error={jobs.error} />
        ) : !jobs.data?.length ? (
          <EmptyState
            title="Chưa có lượt thu thập"
            detail="Job đầu tiên sẽ xuất hiện sau khi bạn bấm lấy dữ liệu."
          />
        ) : (
          <div className="table-scroll">
            <table className="data-table compact-table">
              <thead>
                <tr>
                  <th>Trạng thái</th>
                  <th>Nguồn</th>
                  <th>Bài viết</th>
                  <th>Bình luận</th>
                  <th>Thời gian</th>
                </tr>
              </thead>
              <tbody>
                {jobs.data.slice(0, 8).map((job) => (
                  <tr key={job.id}>
                    <td>
                      <StatusBadge status={job.status} />
                    </td>
                    <td>{job.source_id}</td>
                    <td>{job.posts_collected}</td>
                    <td>{job.comments_collected}</td>
                    <td>{formatDateTime(job.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}

function Metric({
  label,
  value,
  icon,
  tone,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  tone: string;
}) {
  return (
    <div className="metric-item">
      <span className={`metric-icon metric-${tone}`}>{icon}</span>
      <div>
        <span>{label}</span>
        <strong>{value.toLocaleString("vi-VN")}</strong>
      </div>
    </div>
  );
}
