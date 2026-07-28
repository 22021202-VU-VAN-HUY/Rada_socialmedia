(() => {
  const { helpers, adapters } = globalThis.TalentRadarCollector;

  adapters.threads = {
    async collect(job, onBatch) {
      await helpers.collectByScrolling({
        job,
        onBatch,
        findNodes: () =>
          document.querySelectorAll(
            'article, [data-pressable-container="true"]',
          ),
        extract: (node) => extractThread(node, job),
      });
    },
  };

  function extractThread(node, job) {
    const permalink = helpers.firstLink(node, ["/post/"]);
    if (!permalink) return null;
    const postId = helpers.externalId(permalink, [/\/post\/([^/?#]+)/]);
    const content = helpers.firstText(node, [
      '[dir="auto"] span',
      '[dir="auto"]',
    ]);
    if (!content) return null;
    return {
      key: postId || permalink,
      records: [
        {
          source_id: job.source_id,
          platform: "threads",
          item_type: "post",
          external_id: postId,
          content_text: content,
          permalink,
          published_at: helpers.publishedAt(node),
          ...helpers.author(node, ['a[href^="/@"]', 'a[href*="threads.net/@"]']),
          platform_metadata: { collector: "browser_extension" },
        },
      ],
    };
  }
})();
