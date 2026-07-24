from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from playwright.sync_api import Error as PlaywrightError, Page, sync_playwright

from talent_radar.core.config import Settings
from talent_radar.models import PlatformConnection, Source


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
    ) -> dict:
        executable = self.settings.coccoc_executable_path.resolve()
        user_data_dir = Path(connection.profile_dir).resolve()
        profile_directory = (connection.connection_metadata or {}).get(
            "profile_directory",
            self.settings.coccoc_profile_directory,
        )
        if not executable.is_file():
            raise CollectionError(f"Khong tim thay Coc Coc tai {executable}")
        if not source.source_url:
            raise CollectionError("Nguon chua co URL.")

        if not (user_data_dir / profile_directory).is_dir():
            raise CollectionError(
                f"Khong tim thay profile Coc Coc {profile_directory}."
            )
        browser_args = ["--no-first-run", "--no-default-browser-check"]
        browser_args.append(f"--profile-directory={profile_directory}")
        if not self.settings.browser_headless:
            browser_args.append("--start-minimized")

        with sync_playwright() as playwright:
            try:
                context = playwright.chromium.launch_persistent_context(
                    str(user_data_dir),
                    executable_path=str(executable),
                    headless=self.settings.browser_headless,
                    args=browser_args,
                    viewport={"width": 1440, "height": 1000},
                    locale="vi-VN",
                )
            except PlaywrightError as exc:
                raise CollectionError(
                    "Khong mo duoc profile Huy. Hay dong tat ca cua so Coc Coc roi thu lai."
                ) from exc

            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.set_default_timeout(15_000)
                page.set_default_navigation_timeout(60_000)
                urls = self._post_urls(page, source.source_url, max_posts)
                posts = []
                failures = []
                for url in urls:
                    try:
                        posts.append(self._collect_post(page, url))
                    except CollectionError as exc:
                        failures.append({"url": url, "error": str(exc)})
                if not posts and failures:
                    raise CollectionError(failures[0]["error"])
                return {
                    "crawler": "coccoc-playwright",
                    "collected_at": datetime.now(UTC).isoformat(),
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
                context.close()

    def _post_urls(self, page: Page, source_url: str, max_posts: int) -> list[str]:
        canonical = _canonical_url(source_url)
        if re.search(r"/(?:posts|permalink)/\d+/?$", urlsplit(canonical).path):
            return [canonical]

        page.goto(canonical, wait_until="domcontentloaded")
        self._assert_authenticated(page)
        links: list[str] = []
        for _ in range(10):
            batch = page.eval_on_selector_all(
                "a[href]",
                """els => els.map(a => a.href.split('?')[0]).filter(
                    href => /\\/groups\\/[^/]+\\/(posts|permalink)\\/\\d+\\/?$/.test(href)
                )""",
            )
            links.extend(batch)
            if len(set(links)) >= max_posts:
                break
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
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


_EXTRACT_POST_SCRIPT = r"""() => {
    const clean = value => (value || '').replace(/\u00a0/g, ' ').trim();
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
    return {
        post: {
            url: location.href.split('?')[0],
            external_id: pathMatch ? pathMatch[1] : null,
            author: title.replace(/^Bài viết của /, ''),
            group: root.querySelector('[data-ad-rendering-role=profile_name]')?.innerText || null,
            content: message,
            reaction_count: Number(numbers[0] || 0),
            reported_comment_count: Number(numbers[1] || comments.length),
            collected_comment_count: comments.length,
        },
        comments,
    };
}"""
