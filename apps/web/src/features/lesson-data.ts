"use client";

import { useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { api, unwrap } from "@/lib/api";
import { refresh } from "@/lib/query";

export const keys = {
  lesson: (id: string) => ["lesson", id] as const,
  blocks: (revisionId: string) => ["blocks", revisionId] as const,
  provenance: (blockId: string) => ["provenance", blockId] as const,
  reviewQueue: (revisionId: string) => ["review-queue", revisionId] as const,
  publishCheck: (revisionId: string) => ["publish-check", revisionId] as const,
  history: (lessonId: string) => ["history", lessonId] as const,
  anchors: (sourceRevisionId: string) => ["anchors", sourceRevisionId] as const,
};

export function useLesson(lessonId: string) {
  return useQuery({
    queryKey: keys.lesson(lessonId),
    queryFn: () => unwrap(api.GET("/v1/lessons/{lesson_id}", { params: { path: { lesson_id: lessonId } } })),
  });
}

export function useBlocks(revisionId: string | undefined) {
  return useQuery({
    queryKey: keys.blocks(revisionId ?? ""),
    enabled: !!revisionId,
    queryFn: () =>
      unwrap(api.GET("/v1/revisions/{revision_id}/blocks", { params: { path: { revision_id: revisionId! } } })),
  });
}

export function useProvenance(blockId: string | null) {
  return useQuery({
    queryKey: keys.provenance(blockId ?? ""),
    enabled: !!blockId,
    queryFn: () =>
      unwrap(api.GET("/v1/blocks/{block_id}/provenance", { params: { path: { block_id: blockId! } } })),
  });
}

/** Anchors of every source revision pinned by the lesson (for linking a block to its evidence). */
export function useLessonAnchors(sourceRevisionIds: readonly string[]) {
  return useQuery({
    queryKey: ["lesson-anchors", ...sourceRevisionIds],
    enabled: sourceRevisionIds.length > 0,
    queryFn: async () => {
      const lists = await Promise.all(
        sourceRevisionIds.map((id) =>
          unwrap(
            api.GET("/v1/source-revisions/{source_revision_id}/anchors", {
              params: { path: { source_revision_id: id } },
            }),
          ).then((r) => ({ sourceRevisionId: id, anchors: r.items })),
        ),
      );
      return lists;
    },
  });
}

/** Anything that changes a block can change counts, the queue, the gate and the history: refresh them together. */
export function invalidateLesson(qc: QueryClient, lessonId: string, onlyProvenanceOf?: string) {
  return Promise.all([
    refresh(qc, { queryKey: ["lesson", lessonId] }),
    refresh(qc, { queryKey: ["lessons"] }),
    refresh(qc, { queryKey: ["blocks"] }),
    // A review decision only changes its own block: refetching every card's provenance made N^2 requests (429/500).
    refresh(qc, { queryKey: onlyProvenanceOf ? keys.provenance(onlyProvenanceOf) : ["provenance"] }),
    refresh(qc, { queryKey: ["review-queue"] }),
    refresh(qc, { queryKey: ["publish-check"] }),
    refresh(qc, { queryKey: ["history", lessonId] }),
  ]);
}

export function useRefreshLesson(lessonId: string) {
  const qc = useQueryClient();
  return useCallback(() => invalidateLesson(qc, lessonId), [qc, lessonId]);
}
