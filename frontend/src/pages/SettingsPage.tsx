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
  const [tab, setTab] = useState<"platforms" | "configurations">(
    "platforms",
  );
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
  const configurations = useQuery({
    queryKey: ["run-configurations"],
    queryFn: api.runConfigurations,
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
      void queryClient.invalidateQueries({ queryKey: ["run-configurations"] });
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
        description="Quản lý nền tảng, nguồn và cấu hình chạy thủ công."
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
          className={tab === "configurations" ? "active" : ""}
          onClick={() => setTab("configurations")}
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
        <RunConfigurationsPanel
          connections={connections.data || []}
          sources={sources.data || []}
          configurations={configurations.data || []}
          loading={configurations.isLoading}
          error={configurations.error}
          onNotice={setNotice}
        />
      )}
    </>
  );
}

function RunConfigurationsPanel({
  connections,
  sources,
  configurations,
  loading,
  error,
  onNotice,
}: {
  connections: Awaited<ReturnType<typeof api.connections>>;
  sources: Awaited<ReturnType<typeof api.sources>>;
  configurations: Awaited<ReturnType<typeof api.runConfigurations>>;
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
    void queryClient.invalidateQueries({ queryKey: ["run-configurations"] });
    void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    void queryClient.invalidateQueries({ queryKey: ["overview"] });
  };
  const createConfiguration = useMutation({
    mutationFn: api.createRunConfiguration,
    onSuccess: () => {
      onNotice("Đã lưu cấu hình lượt chạy.");
      refresh();
    },
  });
  const runConfiguration = useMutation({
    mutationFn: api.runConfiguration,
    onSuccess: () => {
      onNotice("Đã đưa lượt thu thập vào hàng đợi.");
      refresh();
    },
  });
  const deleteConfiguration = useMutation({
    mutationFn: api.deleteRunConfiguration,
    onSuccess: refresh,
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!facebookConnection || !sourceId) return;
    createConfiguration.mutate({
      connection_id: facebookConnection.id,
      source_id: sourceId,
      max_posts: maxPosts,
    });
  }

  const mutationError =
    createConfiguration.error ||
    runConfiguration.error ||
    deleteConfiguration.error;

  return (
    <section className="settings-section">
      {mutationError && <ErrorState error={mutationError} />}
      <div className="configuration-layout">
        <form className="configuration-form" onSubmit={submit}>
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
                disabled={createConfiguration.isPending}
              >
                {createConfiguration.isPending && (
                  <LoaderCircle className="spin" size={17} />
                )}
                Tạo cấu hình
              </button>
            </>
          )}
        </form>

        <div className="configuration-list">
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
          ) : configurations.length === 0 ? (
            <EmptyState
              title="Chưa có cấu hình"
              detail="Tạo cấu hình để lưu nguồn và giới hạn cho lượt chạy thủ công."
            />
          ) : (
            configurations.map((configuration) => (
              <div className="configuration-row" key={configuration.id}>
                <div>
                  <strong>{configuration.source_id}</strong>
                  <span>
                    Chạy thủ công · tối đa {configuration.max_posts} bài ·{" "}
                    {statusLabel(configuration.last_status)}
                  </span>
                  <span>
                    Lần cuối: {formatDateTime(configuration.last_run_at)}
                  </span>
                  {configuration.last_error && (
                    <span className="row-error">
                      {configuration.last_error}
                    </span>
                  )}
                </div>
                <div className="row-actions">
                  <button
                    className="icon-button"
                    type="button"
                    onClick={() =>
                      runConfiguration.mutate(configuration.id)
                    }
                    title="Chạy ngay"
                    aria-label="Chạy ngay"
                  >
                    <Play size={17} />
                  </button>
                  <button
                    className="icon-button danger-icon"
                    type="button"
                    onClick={() =>
                      deleteConfiguration.mutate(configuration.id)
                    }
                    title="Xóa cấu hình"
                    aria-label="Xóa cấu hình"
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
