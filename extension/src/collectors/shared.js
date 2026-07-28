globalThis.TalentRadarCollector = {
  adapters: {},
  helpers: {
    text(node) {
      return node?.innerText?.replace(/\s+/g, " ").trim() ?? "";
    },

    firstText(root, selectors) {
      for (const selector of selectors) {
        const value = this.text(root.querySelector(selector));
        if (value) return value;
      }
      return "";
    },

    firstLink(root, patterns) {
      for (const anchor of root.querySelectorAll("a[href]")) {
        const href = anchor.href;
        if (patterns.some((pattern) => href.includes(pattern))) return href;
      }
      return null;
    },

    externalId(url, patterns) {
      if (!url) return null;
      for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match?.[1]) return match[1];
      }
      return null;
    },

    publishedAt(root) {
      const value =
        root.querySelector("time[datetime]")?.getAttribute("datetime") ??
        root.querySelector("[data-utime]")?.getAttribute("data-utime") ??
        this.publishedLabel(root);
      if (!value) return null;
      const numeric = Number(value);
      const date = Number.isFinite(numeric) && String(value).trim() !== ""
        ? new Date(numeric * 1000)
        : this.parsePublishedLabel(value);
      return Number.isNaN(date.getTime()) ? null : date.toISOString();
    },

    publishedLabel(root) {
      for (const anchor of root.querySelectorAll("a[href]")) {
        const href = anchor.href || "";
        if (
          !["/posts/", "story_fbid=", "/permalink/", "/video/"].some(
            (pattern) => href.includes(pattern),
          )
        ) {
          continue;
        }
        const candidates = [
          anchor.getAttribute("aria-label"),
          anchor.getAttribute("title"),
          anchor.innerText,
          anchor.querySelector("[aria-label]")?.getAttribute("aria-label"),
          anchor.querySelector("[title]")?.getAttribute("title"),
        ];
        const value = candidates.find((candidate) =>
          this.looksLikePublishedLabel(candidate),
        );
        if (value) return value;
      }
      return null;
    },

    looksLikePublishedLabel(value) {
      if (!value) return false;
      const normalized = String(value).trim().toLocaleLowerCase("vi");
      return (
        /(?:vừa xong|just now|phút|mins?|minutes?|giờ|hours?|hôm qua|yesterday|ngày|days?)/i.test(
          normalized,
        ) ||
        /\d{1,2}\s+tháng\s+\d{1,2}/i.test(normalized) ||
        /\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?/.test(normalized)
      );
    },

    parsePublishedLabel(value) {
      const raw = String(value).trim();
      const normalized = raw.toLocaleLowerCase("vi");
      const now = new Date();
      if (/vừa xong|just now/.test(normalized)) return now;

      const relativePatterns = [
        {
          pattern: /(\d+)\s*(?:phút|mins?|minutes?|\bm\b)/i,
          milliseconds: 60 * 1000,
        },
        {
          pattern: /(\d+)\s*(?:giờ|hours?|hrs?|\bh\b)/i,
          milliseconds: 60 * 60 * 1000,
        },
        {
          pattern: /(\d+)\s*(?:ngày|days?|\bd\b)/i,
          milliseconds: 24 * 60 * 60 * 1000,
        },
      ];
      for (const { pattern, milliseconds } of relativePatterns) {
        const match = normalized.match(pattern);
        if (match) return new Date(now.getTime() - Number(match[1]) * milliseconds);
      }
      if (/hôm qua|yesterday/.test(normalized)) {
        return new Date(now.getTime() - 24 * 60 * 60 * 1000);
      }

      const vietnameseDate = normalized.match(
        /(\d{1,2})\s+tháng\s+(\d{1,2})(?:[^\d]+(\d{4}))?(?:[^\d]+(\d{1,2}):(\d{2}))?/i,
      );
      if (vietnameseDate) {
        return new Date(
          Number(vietnameseDate[3] || now.getFullYear()),
          Number(vietnameseDate[2]) - 1,
          Number(vietnameseDate[1]),
          Number(vietnameseDate[4] || 12),
          Number(vietnameseDate[5] || 0),
        );
      }

      const parsed = new Date(raw);
      return parsed;
    },

    author(root, selectors) {
      for (const selector of selectors) {
        const node = root.querySelector(selector);
        const displayName = this.text(node);
        if (displayName) {
          return {
            author_display_name: displayName,
            author_profile_url: node.href || null,
          };
        }
      }
      return {};
    },

    async collectByScrolling({
      job,
      findNodes,
      extract,
      onBatch,
      maxPasses = 30,
    }) {
      const seen = new Set();
      let collectedPosts = 0;
      let unchangedPasses = 0;
      let consecutiveOldPosts = 0;
      const publishedSince = new Date(job.published_since).getTime();

      for (let pass = 0; pass < maxPasses; pass += 1) {
        const before = seen.size;
        for (const node of findNodes()) {
          const result = extract(node, collectedPosts);
          if (!result?.key || seen.has(result.key)) continue;
          seen.add(result.key);
          if (!result.records?.length) continue;
          const post = result.records.find((record) => record.item_type === "post");
          const publishedAt = post?.published_at
            ? new Date(post.published_at).getTime()
            : Number.NaN;
          if (!post || !Number.isFinite(publishedAt)) continue;
          if (publishedAt < publishedSince) {
            consecutiveOldPosts += 1;
            if (consecutiveOldPosts >= 6) return;
            continue;
          }
          consecutiveOldPosts = 0;
          await onBatch(result.records.slice(0, 500));
          collectedPosts += 1;
          if (collectedPosts >= job.max_posts) return;
        }

        unchangedPasses = seen.size === before ? unchangedPasses + 1 : 0;
        if (unchangedPasses >= 3) return;
        window.scrollBy({ top: Math.max(window.innerHeight * 0.85, 640) });
        await new Promise((resolve) => setTimeout(resolve, 1200));
      }
    },
  },
};
