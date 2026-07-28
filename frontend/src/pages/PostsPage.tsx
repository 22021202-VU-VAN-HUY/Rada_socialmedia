import { useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import {
  Download,
  LoaderCircle,
  MessageSquare,
  RefreshCw,
  Search,
  ThumbsUp,
} from "lucide-react";
import { api } from "../api";
import { ContentTable } from "../components/ContentTable";
import { DetailDrawer } from "../components/DetailDrawer";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  Notice,
  PageHeader,
  Pagination,
} from "../components/ui";
import { useJobs } from "../hooks/useJobs";
import { usePersistentState } from "../hooks/usePersistentState";
import type { ContentItem } from "../types";
import { relativeTime, startForRange } from "../utils";

export function PostsPage() {
  const queryClient = useQueryClient();
  const [range, setRange] = usePersistentState("posts:range", "today");
  const [sourceId, setSourceId] = usePersistentState("posts:source", "");
  const [search, setSearch] = usePersistentState("posts:search", "");
  const [draftSearch, setDraftSearch] = useState(search);
  const [page, setPage] = usePersistentState("posts:page", 1);
  const [selected, setSelected] = useState<ContentItem | null>(null);
  const [notice, setNotice] = useState("");
  const sources = useQuery({ queryKey: ["sources"], queryFn: api.sources });
  const jobs = useJobs();
  const posts = useQuery({
    queryKey: ["posts", page, range, sourceId, search],
    queryFn: () =>
      api.posts({
        page,
        page_size: 30,
        search,
        source_id: sourceId,
        published_after: startForRange(range),
      }),
  });
  const collect = useMutation({
    mutationFn: api.collectFacebook,
    onSuccess: (job) => {
      setNotice(`Đã đưa lượt ${job.id.slice(-8)} vào hàng đợi.`);
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      void queryClient.invalidateQueries({ queryKey: ["overview"] });
    },
  });

  const columns = useMemo<ColumnDef<ContentItem>[]>(
    () => [
      {
        header: "Tác giả / nguồn",
        cell: ({ row }) => (
          <div className="primary-cell">
            <strong>{row.original.author || "Không rõ tác giả"}</strong>
            <span>{row.original.group_name || row.original.source_name}</span>
          </div>
        ),
      },
      {
        header: "Nội dung",
        cell: ({ row }) => (
          <div className="content-cell">
            <p>{row.original.content}</p>
            {row.original.matched_terms.length > 0 && (
              <div className="keyword-list compact-keywords">
                {row.original.matched_terms.slice(0, 3).map((term) => (
                  <span key={term}>{term}</span>
                ))}
              </div>
            )}
          </div>
        ),
      },
      {
        header: "Tương tác",
        cell: ({ row }) => (
          <div className="engagement-cell">
            <span title="Cảm xúc">
              <ThumbsUp size={14} /> {row.original.reaction_count}
            </span>
            <span title="Bình luận đã lấy">
              <MessageSquare size={14} /> {row.original.collected_comment_count}
            </span>
          </div>
        ),
      },
      {
        header: "Đăng",
        cell: ({ row }) =>
          relativeTime(row.original.published_at, row.original.published_label),
      },
    ],
    [],
  );

  function applySearch(event: FormEvent) {
    event.preventDefault();
    setPage(1);
    setSearch(draftSearch.trim());
  }

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: ["posts"] });
    void queryClient.invalidateQueries({ queryKey: ["jobs"] });
  }

  const active = Boolean(jobs.activeJob);

  return (
    <>
      <PageHeader
        title="Bài viết"
        description="Tất cả bài viết Facebook được đăng trong ngày hôm nay."
        actions={
          <>
            <button
              className="icon-button"
              type="button"
              onClick={refresh}
              title="Đồng bộ dữ liệu"
              aria-label="Đồng bộ dữ liệu"
            >
              <RefreshCw size={18} />
            </button>
            <button
              className="primary-button"
              type="button"
              onClick={() => collect.mutate()}
              disabled={active || collect.isPending}
            >
              {active || collect.isPending ? (
                <LoaderCircle className="spin" size={18} />
              ) : (
                <Download size={18} />
              )}
              {active
                ? `Đang lấy ${jobs.activeJob?.posts_collected || 0} bài`
                : "Lấy bài viết hôm nay"}
            </button>
          </>
        }
      />

      <div className="filter-bar">
        <form className="search-field" onSubmit={applySearch}>
          <Search size={17} />
          <input
            value={draftSearch}
            onChange={(event) => setDraftSearch(event.target.value)}
            placeholder="Tìm trong nội dung..."
            aria-label="Tìm trong bài viết"
          />
        </form>
        <select
          value={sourceId}
          onChange={(event) => {
            setSourceId(event.target.value);
            setPage(1);
          }}
          aria-label="Nguồn dữ liệu"
        >
          <option value="">Tất cả nguồn</option>
          {sources.data
            ?.filter((source) => source.platform === "facebook")
            .map((source) => (
              <option value={source.id} key={source.id}>
                {source.source_name}
              </option>
            ))}
        </select>
        <select
          value={range}
          onChange={(event) => {
            setRange(event.target.value);
            setPage(1);
          }}
          aria-label="Khoảng thời gian"
        >
          <option value="today">Hôm nay</option>
          <option value="7">7 ngày gần đây</option>
          <option value="30">30 ngày gần đây</option>
          <option value="all">Toàn bộ</option>
        </select>
      </div>

      {notice && <Notice tone="success">{notice}</Notice>}
      {collect.error && <ErrorState error={collect.error} />}
      {jobs.activeJob && (
        <Notice>
          Bài viết hôm nay sẽ xuất hiện trong bảng ngay khi extension thu thập được.
        </Notice>
      )}

      <section className="data-surface">
        {posts.isLoading ? (
          <LoadingState label="Đang tải bài viết" />
        ) : posts.error ? (
          <ErrorState error={posts.error} />
        ) : !posts.data?.items.length ? (
          <EmptyState
            title="Không có bài viết"
            detail="Thử đổi khoảng thời gian hoặc chạy một lượt lấy dữ liệu mới."
          />
        ) : (
          <>
            <ContentTable
              data={posts.data.items}
              columns={columns}
              selectedId={selected?.id}
              onSelect={setSelected}
            />
            <Pagination
              page={posts.data.page}
              pages={posts.data.pages}
              total={posts.data.total}
              onPage={setPage}
            />
          </>
        )}
      </section>
      <DetailDrawer item={selected} onClose={() => setSelected(null)} />
    </>
  );
}
