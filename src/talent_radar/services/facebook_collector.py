from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from playwright.sync_api import Error as PlaywrightError, Page, sync_playwright

from talent_radar.core.config import Settings
from talent_radar.models import PlatformConnection, Source
from talent_radar.services.browser_profiles import (
    BrowserProfileError,
    ensure_controlled_coccoc,
)


class CollectionError(RuntimeError):
    pass


class LoginRequiredError(CollectionError):
    pass


class FacebookCollector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def collect(
        self,
        connection: PlatformConnection,
        source: Source,
        max_posts: int,
        *,
        since: datetime | None = None,
    ) -> dict:
        if not source.source_url:
            raise CollectionError("Nguon chua co URL.")

        try:
            debug_port, _ = ensure_controlled_coccoc(
                self.settings,
                source.source_url,
                minimized=True,
            )
        except BrowserProfileError as exc:
            raise CollectionError(str(exc)) from exc

        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.connect_over_cdp(
                    f"http://127.0.0.1:{debug_port}"
                )
                if not browser.contexts:
                    raise CollectionError("Coc Coc khong co browser context.")
                context = browser.contexts[0]
            except PlaywrightError as exc:
                raise CollectionError(
                    "Khong gan duoc collector vao Coc Coc cua Talent Radar."
                ) from exc

            page = context.new_page()
            try:
                page.set_default_timeout(15_000)
                page.set_default_navigation_timeout(60_000)
                urls = self._post_urls(page, source.source_url, max_posts)
                posts = []
                failures = []
                consecutive_old_posts = 0
                for url in urls:
                    try:
                        item = self._collect_post(page, url)
                        published_at = _published_at(
                            item["post"],
                            now=datetime.now(
                                ZoneInfo(self.settings.collection_timezone)
                            ),
                        )
                        if published_at is not None:
                            item["post"]["published_at"] = published_at.isoformat()
                        elif since is not None:
                            failures.append(
                                {
                                    "url": url,
                                    "error": "Khong doc duoc thoi gian dang bai.",
                                }
                            )
                            continue
                        if (
                            since is not None
                            and published_at < since
                        ):
                            consecutive_old_posts += 1
                            if consecutive_old_posts >= 5:
                                break
                            continue
                        consecutive_old_posts = 0
                        posts.append(item)
                    except CollectionError as exc:
                        failures.append({"url": url, "error": str(exc)})
                if not posts and failures:
                    raise CollectionError(failures[0]["error"])
                return {
                    "crawler": "coccoc-playwright",
                    "collected_at": datetime.now(UTC).isoformat(),
                    "since": since.isoformat() if since is not None else None,
                    "source_id": source.id,
                    "source_group_url": source.source_url
                    if "/groups/" in source.source_url and "/posts/" not in source.source_url
                    else None,
                    "source_post_url": source.source_url
                    if "/posts/" in source.source_url or "/permalink/" in source.source_url
                    else None,
                    "posts": posts,
                    "failures": failures,
                }
            finally:
                page.close()

    def _post_urls(self, page: Page, source_url: str, max_posts: int) -> list[str]:
        canonical = _canonical_url(source_url)
        if re.search(r"/(?:posts|permalink)/\d+/?$", urlsplit(canonical).path):
            return [canonical]

        page.goto(_chronological_group_url(canonical), wait_until="domcontentloaded")
        self._assert_authenticated(page)
        links: list[str] = []
        unchanged_scrolls = 0
        for _ in range(60):
            batch = page.eval_on_selector_all(
                "a[href]",
                """els => els.map(a => a.href.split('?')[0]).filter(
                    href => /\\/groups\\/[^/]+\\/(posts|permalink)\\/\\d+\\/?$/.test(href)
                )""",
            )
            previous_count = len(set(links))
            links.extend(batch)
            if len(set(links)) >= max_posts:
                break
            unchanged_scrolls = (
                unchanged_scrolls + 1
                if len(set(links)) == previous_count
                else 0
            )
            if unchanged_scrolls >= 15:
                break
            page.evaluate(
                "window.scrollBy(0, Math.max(window.innerHeight * 2, 1200))"
            )
            page.wait_for_timeout(900)
        unique = list(dict.fromkeys(_canonical_url(link) for link in links))
        if not unique:
            raise CollectionError("Khong tim thay bai viet trong group.")
        return unique[:max_posts]

    def _collect_post(self, page: Page, url: str) -> dict:
        page.goto(url, wait_until="domcontentloaded")
        self._assert_authenticated(page)
        page.wait_for_timeout(2500)
        self._select_all_comments(page)
        self._expand_replies(page)
        payload = page.evaluate(_EXTRACT_POST_SCRIPT)
        if not payload:
            raise CollectionError("Khong tim thay noi dung bai viet hoac hop thoai bai viet.")
        payload["post"]["url"] = _canonical_url(page.url)
        return {
            **payload,
            "collected_at": datetime.now(UTC).isoformat(),
        }

    @staticmethod
    def _assert_authenticated(page: Page) -> None:
        current = page.url.casefold()
        if "/login" in current or "/checkpoint" in current:
            raise LoginRequiredError("Facebook can dang nhap lai trong Settings.")
        login_fields = page.locator("input[name='email'], input[name='pass']")
        if login_fields.count() and login_fields.first.is_visible():
            raise LoginRequiredError("Facebook can dang nhap lai trong Settings.")

    @staticmethod
    def _select_all_comments(page: Page) -> None:
        page.evaluate(
            """() => {
                const labels = ['Phù hợp nhất', 'Most relevant'];
                const button = [...document.querySelectorAll('[role=button]')]
                    .find(e => labels.includes((e.innerText || '').trim()));
                if (button) button.click();
            }"""
        )
        page.wait_for_timeout(700)
        page.evaluate(
            """() => {
                const labels = ['Tất cả bình luận', 'All comments'];
                const item = [...document.querySelectorAll('[role=menuitem],[role=button]')]
                    .find(e => labels.some(label => (e.innerText || '').trim().startsWith(label)));
                if (item) item.click();
            }"""
        )
        page.wait_for_timeout(1800)

    @staticmethod
    def _expand_replies(page: Page) -> None:
        for _ in range(4):
            clicked = page.evaluate(
                """() => {
                    const pattern = /^(Xem|View).*(phản hồi|repl)/i;
                    const buttons = [...document.querySelectorAll('[role=button]')]
                        .filter(e => pattern.test((e.innerText || '').trim()));
                    buttons.forEach(e => e.click());
                    return buttons.length;
                }"""
            )
            if not clicked:
                break
            page.wait_for_timeout(1000)


def _canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme or "https", parts.netloc, parts.path.rstrip("/") + "/", "", ""))


def _chronological_group_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            "sorting_setting=CHRONOLOGICAL",
            "",
        )
    )


def _published_at(post: dict, *, now: datetime) -> datetime | None:
    raw = post.get("published_at")
    if isinstance(raw, str) and raw:
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=parsed.tzinfo or UTC).astimezone(UTC)
        except ValueError:
            pass
    label = str(post.get("published_label") or "").strip().casefold()
    if not label:
        return None
    if label in {"vừa xong", "just now"}:
        return now
    if label.startswith(("hôm qua", "yesterday")):
        time_match = re.search(r"(\d{1,2}):(\d{2})", label)
        yesterday = now - timedelta(days=1)
        return yesterday.replace(
            hour=int(time_match.group(1)) if time_match else 0,
            minute=int(time_match.group(2)) if time_match else 0,
            second=0,
            microsecond=0,
        )
    relative_units = {
        "phút": "minutes",
        "minute": "minutes",
        "min": "minutes",
        "giờ": "hours",
        "hour": "hours",
        "hr": "hours",
        "ngày": "days",
        "day": "days",
    }
    relative = re.search(
        r"(\d+)\s*(phút|minutes?|mins?|giờ|hours?|hrs?|ngày|days?)",
        label,
    )
    if relative:
        amount = int(relative.group(1))
        unit = relative.group(2).rstrip("s")
        normalized = relative_units.get(unit)
        if normalized is not None:
            return now - timedelta(**{normalized: amount})
    absolute = re.search(
        r"(\d{1,2})\s+tháng\s+(\d{1,2})(?:\s*,?\s*(\d{4}))?"
        r"(?:\s+lúc\s+(\d{1,2}):(\d{2}))?",
        label,
    )
    if absolute:
        day, month = int(absolute.group(1)), int(absolute.group(2))
        year = int(absolute.group(3) or now.year)
        hour = int(absolute.group(4) or 0)
        minute = int(absolute.group(5) or 0)
        try:
            return datetime(
                year,
                month,
                day,
                hour,
                minute,
                tzinfo=now.tzinfo or UTC,
            )
        except ValueError:
            return None
    return None


_EXTRACT_POST_SCRIPT = r"""() => {
    const clean = value => (value || '').replace(/\u00a0/g, ' ').trim();
    const renderedText = element => {
        if (!element) return '';
        const pieces = [...element.querySelectorAll('span')]
            .filter(node => node.children.length === 0 && node.innerText)
            .map(node => {
                const rect = node.getBoundingClientRect();
                const style = getComputedStyle(node);
                return {
                    text: node.innerText,
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height,
                    visibility: style.visibility,
                    opacity: style.opacity,
                };
            })
            .filter(piece =>
                piece.width > 0
                && piece.height > 0
                && piece.visibility !== 'hidden'
                && piece.opacity !== '0'
            );
        const rows = [];
        for (const piece of pieces) {
            let row = rows.find(candidate => Math.abs(candidate.y - piece.y) <= 2);
            if (!row) {
                row = {y: piece.y, pieces: []};
                rows.push(row);
            }
            row.pieces.push(piece);
        }
        const visibleRow = rows
            .map(row => ({
                ...row,
                distinctPositions: new Set(
                    row.pieces.map(piece => Math.round(piece.x))
                ).size,
            }))
            .sort((a, b) =>
                b.distinctPositions - a.distinctPositions || a.y - b.y
            )[0];
        if (!visibleRow || visibleRow.distinctPositions < 2) {
            return clean(element.innerText);
        }
        return clean(
            visibleRow.pieces
                .sort((a, b) => a.x - b.x)
                .map(piece => piece.text)
                .join('')
        );
    };
    const dialogs = [...document.querySelectorAll('[role=dialog]')];
    const roots = dialogs.length ? dialogs : [document];
    const root = roots
        .filter(node => node.querySelector('[data-ad-rendering-role=story_message]'))
        .sort((a, b) => (b.innerText || '').length - (a.innerText || '').length)[0];
    if (!root) return null;

    const comments = [...root.querySelectorAll('[role=article]')].map((element, index) => {
        const lines = (element.innerText || '').split('\n').map(clean).filter(
            line => line && line !== '·' && line !== 'Trả lời' && line !== 'Reply'
        );
        const aria = element.getAttribute('aria-label') || '';
        const raw = [...element.querySelectorAll('a[href]')]
            .map(anchor => anchor.href)
            .find(href => href.includes('comment_id='));
        let permalink = null;
        let externalId = null;
        let parentExternalId = null;
        if (raw) {
            const parsed = new URL(raw);
            const commentId = parsed.searchParams.get('comment_id');
            const replyId = parsed.searchParams.get('reply_comment_id');
            externalId = replyId || commentId;
            parentExternalId = replyId ? commentId : null;
            permalink = parsed.origin + parsed.pathname + '?comment_id=' + commentId
                + (replyId ? '&reply_comment_id=' + replyId : '');
        }
        const parentMatch = aria.match(/^Phản hồi bình luận của (.+) dưới tên /)
            || aria.match(/đáp lại phản hồi của (.+) vào /);
        return {
            index: index + 1,
            external_id: externalId,
            parent_external_id: parentExternalId,
            author: lines[0] || null,
            published_label: lines[1] || null,
            content: lines.slice(2).join('\n'),
            is_reply: Boolean(parentExternalId),
            parent_author: parentMatch ? parentMatch[1] : null,
            permalink,
            aria_label: aria,
        };
    });

    const message = root.querySelector('[data-ad-rendering-role=story_message]')?.innerText || '';
    const title = (root.innerText || '').split('\n')[0] || '';
    const numbers = [...root.querySelectorAll('[role=button]')]
        .map(element => clean(element.innerText))
        .filter(value => /^\d+$/.test(value));
    const pathMatch = location.href.match(/\/(?:permalink|posts)\/(\d+)/);
    const timestampElement = root.querySelector(
        '[data-utime], time[datetime], abbr[data-utime]'
    );
    const timestampValue = timestampElement?.getAttribute('data-utime');
    const publishedAt = timestampValue
        ? new Date(Number(timestampValue) * 1000).toISOString()
        : timestampElement?.getAttribute('datetime') || null;
    const permalinkAnchor = [...root.querySelectorAll('a[href]')].find(
        anchor =>
            /\/(?:permalink|posts)\/\d+/.test(anchor.href)
            && !anchor.href.includes('comment_id=')
    );
    const publishedLabel = clean(
        timestampElement?.getAttribute('aria-label')
        || timestampElement?.getAttribute('title')
        || timestampElement?.innerText
        || permalinkAnchor?.getAttribute('aria-label')
        || permalinkAnchor?.getAttribute('title')
        || renderedText(permalinkAnchor)
    );
    return {
        post: {
            url: location.href.split('?')[0],
            external_id: pathMatch ? pathMatch[1] : null,
            author: title.replace(/^Bài viết của /, ''),
            group: root.querySelector('[data-ad-rendering-role=profile_name]')?.innerText || null,
            content: message,
            published_at: publishedAt,
            published_label: publishedLabel || null,
            reaction_count: Number(numbers[0] || 0),
            reported_comment_count: Number(numbers[1] || comments.length),
            collected_comment_count: comments.length,
        },
        comments,
    };
}"""
