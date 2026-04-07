import { useCallback, useEffect, useState } from "react";
import { fetchConversations } from "@/lib/api";
import { groupByDateBucket } from "@/lib/utils";
import type { ConversationSummary } from "@/lib/types";

export function useConversationList() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await fetchConversations({ limit: 100 });
      setConversations(data);
    } catch {
      // Silently fail — server might not be running
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const grouped = groupByDateBucket(conversations);

  return {
    conversations,
    grouped,
    isLoading,
    refetch: load,
  };
}
