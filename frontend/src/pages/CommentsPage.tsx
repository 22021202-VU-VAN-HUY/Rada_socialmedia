import { useMemo, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { CornerDownRight, Search } from "lucide-react";
import { api } from "../api";
import { ContentTable } from "../components/ContentTable";
import { DetailDrawer } from "../components/DetailDrawer";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  Pagination,
} from "../components/ui";
import { usePersistentState } from "../hooks/usePersistentState";
import type { ContentItem } from "../types";
import { relativeTime, startForRange } from "../utils";

export function CommentsPage() {
  const [range, setRange] = usePersistentState("comments:range", "today");
  const [sourceId, setSourceId] = usePersistentState("comments:source", "");
  const [search, setSearch] = usePersistentState("comments:search", "");
  const [draftSearch, setDraftSearch] = useState(search);
  const [page, setPage] = usePersistentState("comments:page", 1);
  const [selected, setSelected] = useState<ContentItem | null>(null);
  const sources = useQuery({ queryKey: ["sources"], queryFn: api.sources });
  const comments = useQuery({
    queryKey: ["comments", page, range, sourceId, search],
    queryFn: () =>
      api.comments({
        page,
        page_size: 30,
        search,
        source_id: sourceId,
        published_after: startForRange(range),
      }),
  });

  const columns = useMemo<ColumnDef<ContentItem>[]>(
    () => [
      {
        header: "Tác giả",
        cell: ({ row }) => (
          <div className="primary-cell">
            <strong>{row.original.author || "Không rõ tác giả"}</strong>
            <span>{row.original.source_name}</span>
          </div>
        ),
      },
      {
        header: "Nội dung",
        cell: ({ row }) => (
          <div className="comment-content-cell">
            {row.original.is_reply && <CornerDownRight size={15} />}
            <p>{row.original.content}</p>
          </div>
        ),
      },
      {
        header: "Loại",
        cell: ({ row }) => (
          <span className="type-label">
            {row.original.is_reply ? "Phản hồi" : "Bình luận"}
          </span>
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

  return (
    <>
      <PageHeader
        title="Bình luận"
        description="Bình luận và phản hồi thuộc các bài viết đã thu thập."
      />
      <div className="filter-bar">
        <form className="search-field" onSubmit={applySearch}>
          <Search size={17} />
          <input
            value={draftSearch}
            onChange={(event) => setDraftSearch(event.target.value)}
            placeholder="Tìm trong bình luận..."
            aria-label="Tìm trong bình luận"
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
      <section className="data-surface">
        {comments.isLoading ? (
          <LoadingState label="Đang tải bình luận" />
        ) : comments.error ? (
          <ErrorState error={comments.error} />
        ) : !comments.data?.items.length ? (
          <EmptyState
            title="Không có bình luận"
            detail="Bình luận sẽ xuất hiện sau khi crawler mở bài viết phù hợp."
          />
        ) : (
          <>
            <ContentTable
              data={comments.data.items}
              columns={columns}
              selectedId={selected?.id}
              onSelect={setSelected}
            />
            <Pagination
              page={comments.data.page}
              pages={comments.data.pages}
              total={comments.data.total}
              onPage={setPage}
            />
          </>
        )}
      </section>
      <DetailDrawer item={selected} onClose={() => setSelected(null)} />
    </>
  );
}
