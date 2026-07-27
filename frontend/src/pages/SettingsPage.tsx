import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ExternalLink,
  Link2Off,
  LoaderCircle,
  Play,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { api } from "../api";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  Notice,
  PageHeader,
  StatusBadge,
} from "../components/ui";
import { formatDateTime, statusLabel } from "../utils";

const platformLabels: Record<string, string> = {
  facebook: "Facebook",
  tiktok: "TikTok",
  threads: "Threads",
};

export function SettingsPage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"platforms" | "schedules">("platforms");
  const [notice, setNotice] = useState("");
  const connections = useQuery({
    queryKey: ["connections"],
    queryFn: api.connections,
    refetchInterval: (state) =>
      state.state.data?.some((item) =>
        ["pending_login", "pending_authorization"].includes(item.status),
      )
        ? 2_000
        : false,
  });
  const schedules = useQuery({
    queryKey: ["schedules"],
    queryFn: api.schedules,
  });
  const sources = useQuery({ queryKey: ["sources"], queryFn: api.sources });
  const connectionAction = useMutation({
    mutationFn: ({
      platform,
      action,
    }: {
      platform: string;
      action: "connect" | "disconnect";
    }) =>
      action === "connect"
        ? api.connect(platform)
        : api.disconnect(platform),
    onSuccess: (result) => {
      setNotice(result.message);
      void queryClient.invalidateQueries({ queryKey: ["connections"] });
      void queryClient.invalidateQueries({ queryKey: ["overview"] });
      void queryClient.invalidateQueries({ queryKey: ["schedules"] });
    },
  });
  const syncSources = useMutation({
    mutationFn: api.syncSources,
    onSuccess: () => {
      setNotice("Đã đồng bộ danh sách nguồn.");
      void queryClient.invalidateQueries({ queryKey: ["sources"] });
    },
  });

  return (
    <>
      <PageHeader
        title="Cài đặt"
        description="Quản lý nền tảng, nguồn và lịch thu thập."
      />
      <div className="settings-tabs" role="tablist">
        <button
          type="button"
          className={tab === "platforms" ? "active" : ""}
          onClick={() => setTab("platforms")}
        >
          Nền tảng
        </button>
        <button
          type="button"
          className={tab === "schedules" ? "active" : ""}
          onClick={() => setTab("schedules")}
        >
          Cấu hình lượt chạy
        </button>
      </div>
      {notice && <Notice tone="success">{notice}</Notice>}
      {connectionAction.error && <ErrorState error={connectionAction.error} />}
      {syncSources.error && <ErrorState error={syncSources.error} />}

      {tab === "platforms" ? (
        <section className="settings-section">
          <div className="section-heading">
            <div>
              <h2>Kết nối nền tảng</h2>
              <p>Phiên đăng nhập được mở bằng trình duyệt mặc định của Windows.</p>
            </div>
          </div>
          {connections.isLoading ? (
            <LoadingState />
          ) : connections.error ? (
            <ErrorState error={connections.error} />
          ) : (
            <div className="platform-list">
              {connections.data?.map((connection) => {
                const connected = connection.status === "connected";
                const pending = ["pending_login", "pending_authorization"].includes(
                  connection.status,
                );
                const busy =
                  connectionAction.isPending &&
                  connectionAction.variables?.platform === connection.platform;
                return (
                  <div className="platform-row" key={connection.id}>
                    <div className={`platform-logo logo-${connection.platform}`}>
                      {platformLabels[connection.platform]?.slice(0, 1) ||
                        connection.platform.slice(0, 1).toUpperCase()}
                    </div>
                    <div className="platform-info">
                      <div>
                        <h3>
                          {platformLabels[connection.platform] ||
                            connection.platform}
                        </h3>
                        <StatusBadge status={connection.status} />
                      </div>
                      <p>
                        {connection.connected_account_name ||
                          connection.profile_account_name ||
                          "Chưa xác định tài khoản"}
                      </p>
                      {connection.last_error && (
                        <span className="row-error">{connection.last_error}</span>
                      )}
                    </div>
                    <div className="row-actions">
                      {!connected && (
                        <button
                          className="secondary-button"
                          type="button"
                          disabled={busy}
                          onClick={() =>
                            connectionAction.mutate({
                              platform: connection.platform,
                              action: "connect",
                            })
                          }
                        >
                          {busy ? (
                            <LoaderCircle className="spin" size={17} />
                          ) : (
                            <ExternalLink size={17} />
                          )}
                          {pending ? "Mở lại" : "Liên kết"}
                        </button>
                      )}
                      {(connected || pending) && (
                        <button
                          className="danger-button"
                          type="button"
                          disabled={busy}
                          onClick={() =>
                            connectionAction.mutate({
                              platform: connection.platform,
                              action: "disconnect",
                            })
                          }
                        >
                          <Link2Off size={17} />
                          Ngắt kết nối
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          <div className="source-toolbar">
            <div>
              <h2>Nguồn dữ liệu</h2>
              <p>{sources.data?.length || 0} nguồn trong registry.</p>
            </div>
            <button
              className="secondary-button"
              type="button"
              onClick={() => syncSources.mutate()}
              disabled={syncSources.isPending}
            >
              <RefreshCw
                className={syncSources.isPending ? "spin" : ""}
                size={17}
              />
              Đồng bộ nguồn
            </button>
          </div>
        </section>
      ) : (
        <SchedulesPanel
          connections={connections.data || []}
          sources={sources.data || []}
          schedules={schedules.data || []}
          loading={schedules.isLoading}
          error={schedules.error}
          onNotice={setNotice}
        />
      )}
    </>
  );
}

function SchedulesPanel({
  connections,
  sources,
  schedules,
  loading,
  error,
  onNotice,
}: {
  connections: Awaited<ReturnType<typeof api.connections>>;
  sources: Awaited<ReturnType<typeof api.sources>>;
  schedules: Awaited<ReturnType<typeof api.schedules>>;
  loading: boolean;
  error: unknown;
  onNotice: (message: string) => void;
}) {
  const queryClient = useQueryClient();
  const facebookConnection = connections.find(
    (item) => item.platform === "facebook" && item.status === "connected",
  );
  const facebookSources = sources.filter(
    (item) => item.platform === "facebook" && item.enabled,
  );
  const [sourceId, setSourceId] = useState("");
  const [maxPosts, setMaxPosts] = useState(20);
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["schedules"] });
    void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    void queryClient.invalidateQueries({ queryKey: ["overview"] });
  };
  const createSchedule = useMutation({
    mutationFn: api.createSchedule,
    onSuccess: () => {
      onNotice("Đã tạo lịch thu thập.");
      refresh();
    },
  });
  const runSchedule = useMutation({
    mutationFn: api.runSchedule,
    onSuccess: () => {
      onNotice("Đã đưa lượt thu thập vào hàng đợi.");
      refresh();
    },
  });
  const deleteSchedule = useMutation({
    mutationFn: api.deleteSchedule,
    onSuccess: refresh,
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!facebookConnection || !sourceId) return;
    createSchedule.mutate({
      connection_id: facebookConnection.id,
      source_id: sourceId,
      interval_minutes: 1440,
      max_posts: maxPosts,
      enabled: false,
    });
  }

  const mutationError =
    createSchedule.error ||
    runSchedule.error ||
    deleteSchedule.error;

  return (
    <section className="settings-section">
      {mutationError && <ErrorState error={mutationError} />}
      <div className="schedule-layout">
        <form className="schedule-form" onSubmit={submit}>
          <div className="section-heading">
            <div>
              <h2>Tạo cấu hình</h2>
              <p>Cấu hình chỉ chạy sau khi bạn chủ động bấm nút Play.</p>
            </div>
          </div>
          {!facebookConnection ? (
            <Notice tone="warning">Hãy liên kết Facebook trước.</Notice>
          ) : (
            <>
              <label>
                Nguồn
                <select
                  value={sourceId}
                  onChange={(event) => setSourceId(event.target.value)}
                  required
                >
                  <option value="">Chọn nguồn</option>
                  {facebookSources.map((source) => (
                    <option value={source.id} key={source.id}>
                      {source.source_name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Số bài tối đa
                <input
                  type="number"
                  min={1}
                  max={200}
                  value={maxPosts}
                  onChange={(event) => setMaxPosts(Number(event.target.value))}
                />
              </label>
              <button
                className="primary-button"
                disabled={createSchedule.isPending}
              >
                {createSchedule.isPending && (
                  <LoaderCircle className="spin" size={17} />
                )}
                Tạo cấu hình
              </button>
            </>
          )}
        </form>

        <div className="schedule-list">
          <div className="section-heading">
            <div>
              <h2>Cấu hình đã lưu</h2>
              <p>Không cấu hình nào tự chạy trong nền.</p>
            </div>
          </div>
          {loading ? (
            <LoadingState />
          ) : error ? (
            <ErrorState error={error} />
          ) : schedules.length === 0 ? (
            <EmptyState
              title="Chưa có cấu hình"
              detail="Tạo cấu hình để lưu nguồn và giới hạn cho lượt chạy thủ công."
            />
          ) : (
            schedules.map((schedule) => (
              <div className="schedule-row" key={schedule.id}>
                <div>
                  <strong>{schedule.source_id}</strong>
                  <span>
                    Chạy thủ công · tối đa {schedule.max_posts} bài ·{" "}
                    {statusLabel(schedule.last_status)}
                  </span>
                  <span>Lần cuối: {formatDateTime(schedule.last_run_at)}</span>
                  {schedule.last_error && (
                    <span className="row-error">{schedule.last_error}</span>
                  )}
                </div>
                <div className="row-actions">
                  <button
                    className="icon-button"
                    type="button"
                    onClick={() => runSchedule.mutate(schedule.id)}
                    title="Chạy ngay"
                    aria-label="Chạy ngay"
                  >
                    <Play size={17} />
                  </button>
                  <button
                    className="icon-button danger-icon"
                    type="button"
                    onClick={() => deleteSchedule.mutate(schedule.id)}
                    title="Xóa lịch"
                    aria-label="Xóa lịch"
                  >
                    <Trash2 size={17} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
