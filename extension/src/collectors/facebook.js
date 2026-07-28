(() => {
  const { helpers, adapters } = globalThis.TalentRadarCollector;

  adapters.facebook = {
    async collect(job, onBatch) {
      await helpers.collectByScrolling({
        job,
        onBatch,
        findNodes: () =>
          document.querySelectorAll(
            '[role="feed"] [role="article"], [data-pagelet^="FeedUnit"]',
          ),
        extract: (article) => extractArticle(article, job),
      });
    },
  };

  function extractArticle(article, job) {
    const permalink = helpers.firstLink(article, [
      "/posts/",
      "story_fbid=",
      "/permalink/",
    ]);
    if (!permalink) return null;
    const postId = helpers.externalId(permalink, [
      /\/posts\/(\d+)/,
      /story_fbid=(\d+)/,
      /\/permalink\/(\d+)/,
    ]);
    const content = helpers.firstText(article, [
      '[data-ad-preview="message"]',
      '[data-ad-comet-preview="message"]',
      '[dir="auto"]',
    ]);
    if (!content) return null;

    const records = [
      {
        source_id: job.source_id,
        platform: "facebook",
        item_type: "post",
        external_id: postId,
        content_text: content,
        permalink,
        published_at: helpers.publishedAt(article),
        ...helpers.author(article, [
          "h2 a[href]",
          "h3 a[href]",
          'a[role="link"][tabindex="0"]',
        ]),
        platform_metadata: { collector: "browser_extension" },
      },
    ];

    const commentNodes = article.querySelectorAll(
      '[aria-label^="Comment by"], [aria-label^="Binh luan cua"], ul li',
    );
    let commentCount = 0;
    for (const comment of commentNodes) {
      if (commentCount >= job.max_comments_per_post) break;
      const commentText = helpers.firstText(comment, [
        '[dir="auto"]',
        '[data-ad-preview="message"]',
      ]);
      if (!commentText || commentText === content) continue;
      const commentLink = helpers.firstLink(comment, ["comment_id=", "/comments/"]);
      const commentId = helpers.externalId(commentLink, [
        /comment_id=(\d+)/,
        /\/comments\/(\d+)/,
      ]);
      records.push({
        source_id: job.source_id,
        platform: "facebook",
        item_type: "comment",
        external_id: commentId,
        parent_external_id: postId,
        root_external_id: postId,
        content_text: commentText,
        permalink: commentLink || permalink,
        published_at: helpers.publishedAt(comment),
        ...helpers.author(comment, ['a[role="link"]', "a[href]"]),
        platform_metadata: { collector: "browser_extension" },
      });
      commentCount += 1;
    }

    return { key: postId || permalink, records };
  }
})();
