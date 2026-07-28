(() => {
  const { helpers, adapters } = globalThis.TalentRadarCollector;

  adapters.tiktok = {
    async collect(job, onBatch) {
      await helpers.collectByScrolling({
        job,
        onBatch,
        findNodes: () =>
          document.querySelectorAll(
            '[data-e2e="recommend-list-item-container"], [data-e2e="user-post-item"], article',
          ),
        extract: (node) => extractVideo(node, job),
      });
    },
  };

  function extractVideo(node, job) {
    const permalink = helpers.firstLink(node, ["/video/"]);
    if (!permalink) return null;
    const videoId = helpers.externalId(permalink, [/\/video\/(\d+)/]);
    const content =
      helpers.firstText(node, [
        '[data-e2e="browse-video-desc"]',
        '[data-e2e="video-desc"]',
        '[data-e2e="search-card-video-caption"]',
      ]) || node.querySelector("img[alt]")?.getAttribute("alt")?.trim();
    if (!content) return null;

    const records = [
      {
        source_id: job.source_id,
        platform: "tiktok",
        item_type: "post",
        external_id: videoId,
        content_text: content,
        permalink,
        published_at: helpers.publishedAt(node),
        ...helpers.author(node, [
          '[data-e2e="video-author-uniqueid"]',
          'a[href*="/@"]',
        ]),
        platform_metadata: { collector: "browser_extension", content_kind: "video" },
      },
    ];

    const comments = document.querySelectorAll('[data-e2e="comment-item"]');
    for (const comment of Array.from(comments).slice(
      0,
      job.max_comments_per_post,
    )) {
      const commentText = helpers.firstText(comment, [
        '[data-e2e="comment-level-1"]',
        "p",
      ]);
      if (!commentText) continue;
      records.push({
        source_id: job.source_id,
        platform: "tiktok",
        item_type: "comment",
        parent_external_id: videoId,
        root_external_id: videoId,
        content_text: commentText,
        permalink,
        ...helpers.author(comment, ['a[href*="/@"]']),
        platform_metadata: { collector: "browser_extension" },
      });
    }
    return { key: videoId || permalink, records };
  }
})();
