import { RefreshCw } from "lucide-react";
import { useJobs } from "../hooks/useJobs";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  StatusBadge,
} from "../components/ui";
import { formatDateTime } from "../utils";

export function RunsPage() {
  const jobs = useJobs();
  return (
    <>
      <PageHeader
        title="Lượt thu thập"
        description="Lịch sử các job chạy nền và kết quả tương ứng."
        actions={
          <button
            className="icon-button"
            type="button"
            onClick={() => jobs.refetch()}
            title="Đồng bộ trạng thái"
            aria-label="Đồng bộ trạng thái"
          >
            <RefreshCw size={18} />
          </button>
        }
      />
      <section className="data-surface">
        {jobs.isLoading ? (
          <LoadingState label="Đang tải lịch sử" />
        ) : jobs.error ? (
          <ErrorState error={jobs.error} />
        ) : !jobs.data?.length ? (
          <EmptyState
            title="Chưa có lượt thu thập"
            detail="Bạn có thể bắt đầu từ nút lấy dữ liệu trong mục Bài viết."
          />
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Trạng thái</th>
                  <th>Nguồn</th>
                  <th>Kích hoạt</th>
                  <th>Bài viết</th>
                  <th>Bình luận</th>
                  <th>Bắt đầu</th>
                  <th>Hoàn tất</th>
                </tr>
              </thead>
              <tbody>
                {jobs.data.map((job) => (
                  <tr key={job.id}>
                    <td>
                      <StatusBadge status={job.status} />
                    </td>
                    <td>
                      <div className="primary-cell">
                        <strong>{job.source_id}</strong>
                        {job.error_summary && <span>{job.error_summary}</span>}
                      </div>
                    </td>
                    <td>{job.trigger === "manual" ? "Thủ công" : "Theo lịch"}</td>
                    <td>{job.posts_collected}</td>
                    <td>{job.comments_collected}</td>
                    <td>{formatDateTime(job.started_at || job.created_at)}</td>
                    <td>{formatDateTime(job.completed_at)}</td>
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
