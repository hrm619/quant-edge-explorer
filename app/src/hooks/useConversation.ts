import { useCallback, useReducer, useRef } from "react";
import { fetchConversation } from "@/lib/api";
import { streamChat } from "@/lib/sse";
import type {
  MessageResponse,
  ArtifactDetail,
  Phase,
  StreamingToolCall,
  StreamingArtifact,
  SSEConversationEvent,
  SSEPhaseEvent,
  SSEPlanEvent,
  SSEToolCallStartEvent,
  SSEToolCallEndEvent,
  SSEArtifactEvent,
  SSETextDeltaEvent,
  SSEDoneEvent,
  SSETitleUpdatedEvent,
  SSEErrorEvent,
  ConversationDetail,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

interface ConversationState {
  conversationId: string | null;
  messages: MessageResponse[];
  artifacts: Map<string, ArtifactDetail>;
  streamingToolCalls: Map<string, StreamingToolCall>;
  streamingArtifacts: StreamingArtifact[];
  plan: string | null;
  phase: Phase;
  isStreaming: boolean;
  streamingText: string;
  currentToolName: string | null;
  title: string | null;
  error: string | null;
}

const initialState: ConversationState = {
  conversationId: null,
  messages: [],
  artifacts: new Map(),
  streamingToolCalls: new Map(),
  streamingArtifacts: [],
  plan: null,
  phase: "idle",
  isStreaming: false,
  streamingText: "",
  currentToolName: null,
  title: null,
  error: null,
};

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

type Action =
  | { type: "SET_CONVERSATION"; payload: ConversationDetail }
  | { type: "SSE_CONVERSATION"; payload: SSEConversationEvent }
  | { type: "SSE_PHASE"; payload: SSEPhaseEvent }
  | { type: "SSE_PLAN"; payload: SSEPlanEvent }
  | { type: "SSE_TOOL_CALL_START"; payload: SSEToolCallStartEvent }
  | { type: "SSE_TOOL_CALL_END"; payload: SSEToolCallEndEvent }
  | { type: "SSE_ARTIFACT"; payload: SSEArtifactEvent }
  | { type: "SSE_TEXT_DELTA"; payload: SSETextDeltaEvent }
  | { type: "SSE_DONE"; payload: SSEDoneEvent }
  | { type: "SSE_TITLE_UPDATED"; payload: SSETitleUpdatedEvent }
  | { type: "SSE_ERROR"; payload: SSEErrorEvent }
  | { type: "ADD_USER_MESSAGE"; payload: string }
  | { type: "START_STREAMING" }
  | { type: "RESET" };

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------

function reducer(state: ConversationState, action: Action): ConversationState {
  switch (action.type) {
    case "SET_CONVERSATION": {
      const conv = action.payload;
      const artifacts = new Map<string, ArtifactDetail>();
      // Build artifact map from the conversation's artifact summaries
      // (details are fetched lazily when needed, but we store summaries)
      for (const a of conv.artifacts) {
        artifacts.set(a.id, a as unknown as ArtifactDetail);
      }
      return {
        ...initialState,
        conversationId: conv.id,
        messages: conv.messages,
        artifacts,
        title: conv.title,
      };
    }

    case "SSE_CONVERSATION":
      return { ...state, conversationId: action.payload.conversation_id };

    case "SSE_PHASE":
      return { ...state, phase: action.payload.phase };

    case "SSE_PLAN":
      return { ...state, plan: action.payload.text };

    case "SSE_TOOL_CALL_START": {
      const tc = action.payload;
      const newMap = new Map(state.streamingToolCalls);
      newMap.set(tc.id, { id: tc.id, name: tc.name, input: tc.input });
      return { ...state, streamingToolCalls: newMap, currentToolName: tc.name };
    }

    case "SSE_TOOL_CALL_END": {
      const tc = action.payload;
      const newMap = new Map(state.streamingToolCalls);
      const existing = newMap.get(tc.id);
      if (existing) {
        newMap.set(tc.id, {
          ...existing,
          status: tc.status,
          duration_ms: tc.duration_ms,
          row_count: tc.row_count,
        });
      }
      return { ...state, streamingToolCalls: newMap, currentToolName: null };
    }

    case "SSE_ARTIFACT": {
      const a = action.payload;
      const sa: StreamingArtifact = {
        id: a.id,
        tool_call_id: "", // Will be resolved on reconciliation
        kind: a.kind,
        title: a.title,
        spec: a.spec,
      };
      return {
        ...state,
        streamingArtifacts: [...state.streamingArtifacts, sa],
      };
    }

    case "SSE_TEXT_DELTA":
      return { ...state, streamingText: state.streamingText + action.payload.text };

    case "SSE_DONE":
      return {
        ...state,
        isStreaming: false,
        phase: "idle",
        currentToolName: null,
      };

    case "SSE_TITLE_UPDATED":
      return { ...state, title: action.payload.title };

    case "SSE_ERROR":
      return { ...state, error: action.payload.message, isStreaming: false };

    case "ADD_USER_MESSAGE": {
      const userMsg: MessageResponse = {
        id: `temp-${Date.now()}`,
        conversation_id: state.conversationId ?? "",
        role: "user",
        content: action.payload,
        phase: null,
        created_at: new Date().toISOString(),
        ordinal: state.messages.length,
        tool_calls: [],
      };
      return { ...state, messages: [...state.messages, userMsg] };
    }

    case "START_STREAMING":
      return {
        ...state,
        isStreaming: true,
        streamingText: "",
        streamingToolCalls: new Map(),
        streamingArtifacts: [],
        plan: null,
        phase: "idle",
        error: null,
      };

    case "RESET":
      return { ...initialState };

    default:
      return state;
  }
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useConversation() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const abortRef = useRef<AbortController | null>(null);

  const loadConversation = useCallback(async (id: string) => {
    try {
      const conv = await fetchConversation(id);
      dispatch({ type: "SET_CONVERSATION", payload: conv });
    } catch (err) {
      dispatch({
        type: "SSE_ERROR",
        payload: { message: err instanceof Error ? err.message : "Failed to load conversation" },
      });
    }
  }, []);

  const sendMessage = useCallback(
    async (content: string, onConversationCreated?: (id: string) => void, onTitleUpdated?: () => void) => {
      // Cancel any in-flight stream
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      dispatch({ type: "ADD_USER_MESSAGE", payload: content });
      dispatch({ type: "START_STREAMING" });

      let conversationId = state.conversationId;

      try {
        await streamChat(
          content,
          conversationId,
          (event, data) => {
            switch (event) {
              case "conversation": {
                const d = data as SSEConversationEvent;
                dispatch({ type: "SSE_CONVERSATION", payload: d });
                if (!conversationId) {
                  conversationId = d.conversation_id;
                  onConversationCreated?.(d.conversation_id);
                }
                break;
              }
              case "phase":
                dispatch({ type: "SSE_PHASE", payload: data as SSEPhaseEvent });
                break;
              case "plan":
                dispatch({ type: "SSE_PLAN", payload: data as SSEPlanEvent });
                break;
              case "tool_call_start":
                dispatch({ type: "SSE_TOOL_CALL_START", payload: data as SSEToolCallStartEvent });
                break;
              case "tool_call_end":
                dispatch({ type: "SSE_TOOL_CALL_END", payload: data as SSEToolCallEndEvent });
                break;
              case "artifact":
                dispatch({ type: "SSE_ARTIFACT", payload: data as SSEArtifactEvent });
                break;
              case "text_delta":
                dispatch({ type: "SSE_TEXT_DELTA", payload: data as SSETextDeltaEvent });
                break;
              case "done":
                dispatch({ type: "SSE_DONE", payload: data as SSEDoneEvent });
                break;
              case "title_updated": {
                dispatch({ type: "SSE_TITLE_UPDATED", payload: data as SSETitleUpdatedEvent });
                onTitleUpdated?.();
                break;
              }
              case "error":
                dispatch({ type: "SSE_ERROR", payload: data as SSEErrorEvent });
                break;
            }
          },
          controller.signal
        );

        // Reconcile: fetch full conversation from REST to get properly nested data
        if (conversationId) {
          const conv = await fetchConversation(conversationId);
          dispatch({ type: "SET_CONVERSATION", payload: conv });
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          dispatch({
            type: "SSE_ERROR",
            payload: { message: err instanceof Error ? err.message : "Stream failed" },
          });
        }
      }
    },
    [state.conversationId]
  );

  const newConversation = useCallback(() => {
    abortRef.current?.abort();
    dispatch({ type: "RESET" });
  }, []);

  return {
    ...state,
    sendMessage,
    loadConversation,
    newConversation,
  };
}
