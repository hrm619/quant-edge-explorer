import { useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useConversation } from "@/hooks/useConversation";
import { useConversationList } from "@/hooks/useConversationList";
import { ConnectionStatus } from "@/components/errors/ConnectionStatus";
import { ConversationSidebar } from "@/components/chat/ConversationSidebar";
import { MessageList } from "@/components/chat/MessageList";
import { InputBox } from "@/components/chat/InputBox";
import { ErrorBoundary } from "@/components/errors/ErrorBoundary";

export function ChatRoute() {
  const { conversationId } = useParams();
  const navigate = useNavigate();

  const {
    conversationId: activeConversationId,
    messages,
    artifacts,
    plan,
    phase,
    isStreaming,
    streamingText,
    currentToolName,
    streamingArtifacts,
    error,
    sendMessage,
    loadConversation,
    newConversation,
  } = useConversation();

  const { grouped, isLoading, refetch } = useConversationList();

  // Load conversation when URL changes — but skip if we're already
  // streaming this conversation (the navigate from onConversationCreated
  // would otherwise clobber the in-progress stream).
  useEffect(() => {
    if (conversationId) {
      if (conversationId !== activeConversationId || !isStreaming) {
        loadConversation(conversationId);
      }
    } else {
      newConversation();
    }
  }, [conversationId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSend = useCallback(
    (content: string) => {
      sendMessage(
        content,
        // onConversationCreated — update URL
        (id) => {
          navigate(`/c/${id}`, { replace: true });
          refetch();
        },
        // onTitleUpdated — refresh sidebar
        () => refetch()
      );
    },
    [sendMessage, navigate, refetch]
  );

  const handleNew = useCallback(() => {
    newConversation();
    navigate("/");
  }, [newConversation, navigate]);

  return (
    <div className="flex h-screen">
      <ConversationSidebar
        grouped={grouped}
        isLoading={isLoading}
        onNewConversation={handleNew}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <ConnectionStatus />

        {error && (
          <div className="bg-red-50 border-b border-red-200 px-4 py-2 text-xs text-trust-untrusted">
            {error}
          </div>
        )}

        <ErrorBoundary>
          <MessageList
            messages={messages}
            artifacts={artifacts}
            plan={plan}
            phase={phase}
            isStreaming={isStreaming}
            streamingText={streamingText}
            currentToolName={currentToolName}
            streamingArtifacts={streamingArtifacts}
          />
        </ErrorBoundary>

        <InputBox onSend={handleSend} disabled={isStreaming} />
      </div>
    </div>
  );
}
