import { ExternalLink, MessageSquare, ThumbsUp, X } from "lucide-react";
import type { ContentItem } from "../types";
import { formatDateTime, relativeTime } from "../utils";

export function DetailDrawer({
  item,
  onClose,
}: {
  item: ContentItem | null;
  onClose: () => void;
}) {
  if (!item) return null;
  return (
    <>
      <button
        className="drawer-backdrop"
        type="button"
        onClick={onClose}
        aria-label="Đóng chi tiết"
      />
      <aside className="detail-drawer" aria-label="Chi tiết nội dung">
        <header>
          <div>
            <span className="eyebrow">
              {item.item_type === "post"
                ? "Bài viết"
                : item.is_reply
                  ? "Phản hồi"
                  : "Bình luận"}
            </span>
            <h2>{item.author || "Không rõ tác giả"}</h2>
          </div>
          <button
            className="icon-button"
            type="button"
            onClick={onClose}
            title="Đóng"
            aria-label="Đóng"
          >
            <X size={19} />
          </button>
        </header>
        <div className="drawer-body">
          <dl className="detail-meta">
            <div>
              <dt>Nguồn</dt>
              <dd>{item.group_name || item.source_name}</dd>
            </div>
            <div>
              <dt>Đăng lúc</dt>
              <dd>
                {relativeTime(item.published_at, item.published_label)} ·{" "}
                {formatDateTime(item.published_at)}
              </dd>
            </div>
            {item.topic && (
              <div>
                <dt>Chủ đề</dt>
                <dd>{item.topic}</dd>
              </div>
            )}
          </dl>
          {item.matched_terms.length > 0 && (
            <div className="keyword-list">
              {item.matched_terms.map((term) => (
                <span key={term}>{term}</span>
              ))}
            </div>
          )}
          <p className="detail-content">{item.content}</p>
          {item.item_type === "post" && (
            <div className="engagement-row">
              <span>
                <ThumbsUp size={16} /> {item.reaction_count}
              </span>
              <span>
                <MessageSquare size={16} /> {item.collected_comment_count}
              </span>
            </div>
          )}
          {item.permalink && (
            <a
              className="secondary-button"
              href={item.permalink}
              target="_blank"
              rel="noreferrer"
            >
              <ExternalLink size={17} />
              Mở nội dung gốc
            </a>
          )}
        </div>
      </aside>
    </>
  );
}
