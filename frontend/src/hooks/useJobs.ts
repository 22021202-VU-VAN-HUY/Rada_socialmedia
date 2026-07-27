import { useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";

export function useJobs() {
  const queryClient = useQueryClient();
  const previousProgress = useRef("");
  const query = useQuery({
    queryKey: ["jobs"],
    queryFn: api.jobs,
    refetchInterval: (state) => {
      const jobs = state.state.data;
      return jobs?.some((job) => ["queued", "running"].includes(job.status))
        ? 2_000
        : false;
    },
  });
  const activeJob = query.data?.find((job) =>
    ["queued", "running"].includes(job.status),
  );

  useEffect(() => {
    if (!query.data?.length) return;
    const latest = query.data[0];
    const progress = [
      latest.id,
      latest.status,
      latest.posts_collected,
      latest.comments_collected,
    ].join(":");
    if (previousProgress.current && previousProgress.current !== progress) {
      void queryClient.invalidateQueries({ queryKey: ["posts"] });
      void queryClient.invalidateQueries({ queryKey: ["comments"] });
      void queryClient.invalidateQueries({ queryKey: ["overview"] });
    }
    previousProgress.current = progress;
  }, [query.data, queryClient]);

  return { ...query, activeJob };
}
