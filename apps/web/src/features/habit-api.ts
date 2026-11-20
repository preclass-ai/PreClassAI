import { useQuery } from "@tanstack/react-query";
import { api, unwrap, type Schemas } from "@/lib/api";
import { withTimeout } from "@/lib/http";

export type ChatReply = Schemas["ChatReply"];
export const HABIT_TIMEOUT_MS = 20_000;

/** Habit is off unless the server says so (CHAT_ENABLED): every Habit control hides while this is false or unknown. */
export function useHabitOn(): boolean {
  const cfg = useQuery({
    queryKey: ["auth-config"],
    queryFn: () => unwrap(api.GET("/v1/auth/config")),
    staleTime: Infinity,
    retry: false,
  });
  return cfg.data?.chatEnabled === true;
}

export const habitKey = (assignmentId: string) => ["habit", assignmentId];

export function useHabit(assignmentId: string, enabled: boolean) {
  return useQuery({
    queryKey: habitKey(assignmentId),
    enabled,
    retry: false,
    queryFn: ({ signal }) =>
      unwrap(
        api.GET("/v1/student/assignments/{assignment_id}/habit", {
          params: { path: { assignment_id: assignmentId } },
          signal: withTimeout(HABIT_TIMEOUT_MS, signal),
        }),
      ),
  });
}

/** One Habit call. Reuse `requestId` when retrying the same request: the server then returns the stored reply. */
export function askHabit(assignmentId: string, body: Schemas["ChatRequest"]): Promise<ChatReply> {
  return unwrap(
    api.POST("/v1/student/assignments/{assignment_id}/chat", {
      params: { path: { assignment_id: assignmentId } },
      body,
      signal: withTimeout(HABIT_TIMEOUT_MS),
    }),
  );
}
