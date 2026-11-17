"use client";

import { useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { api, unwrap } from "@/lib/api";

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
export function invalidateLesson(qc: QueryClient, lessonId: string) {
  return Promise.all([
    qc.invalidateQueries({ queryKey: ["lesson", lessonId] }),
    qc.invalidateQueries({ queryKey: ["lessons"] }),
    qc.invalidateQueries({ queryKey: ["blocks"] }),
    qc.invalidateQueries({ queryKey: ["provenance"] }),
    qc.invalidateQueries({ queryKey: ["review-queue"] }),
    qc.invalidateQueries({ queryKey: ["publish-check"] }),
    qc.invalidateQueries({ queryKey: ["history", lessonId] }),
  ]);
}

export function useRefreshLesson(lessonId: string) {
  const qc = useQueryClient();
  return useCallback(() => invalidateLesson(qc, lessonId), [qc, lessonId]);
}
