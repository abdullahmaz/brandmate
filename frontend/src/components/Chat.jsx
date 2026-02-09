import React, { useMemo, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ChatArea } from "./ChatArea";
import { ChatInput } from "./ChatInput";
import { formatDistanceToNow } from "date-fns";
import { useChat, useCreateChat } from "../hooks/useChat";
import { api } from "../services/api";
import { queryKeys } from "../types/api";
import { Button } from "./ui/button";
import { PlusIcon, Search } from "lucide-react";

const Chat = () => {
  const { chatId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [localMessages, setLocalMessages] = useState([]);
  const abortControllerRef = useRef(null);
  const lastAbortRef = useRef(false);

  // Only load chat data if we have a chatId and no local messages
  const { data: chatData, isLoading: chatLoading } = useChat(chatId);

  // Send message mutation with custom onSuccess handler
  const sendMessageMutation = useMutation({
    // Explicitly disable retries so aborted requests don't get retried
    retry: false,
    mutationFn: ({ chatId, data }) => {
      // Clear any previous abort flag and create a new AbortController
      lastAbortRef.current = false;
      abortControllerRef.current = new AbortController();
      return api.sendMessage(chatId, data, abortControllerRef.current.signal);
    },
    onSuccess: (response, variables) => {
      // If we aborted this request, ignore the success handler
      if (lastAbortRef.current) {
        lastAbortRef.current = false;
        abortControllerRef.current = null;
        return;
      }

      const { chatId } = variables;

      // Clear AbortController
      abortControllerRef.current = null;

      // Clear local messages since they'll be replaced by fresh API data
      setLocalMessages([]);

      // Invalidate chat data to refresh messages
      if (chatId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.chat(chatId) });
      }
    },
    onError: (error) => {
      // Clear AbortController
      abortControllerRef.current = null;

      // Don't show error message if request was aborted
      if (error?.name === 'CanceledError' || error?.code === 'ERR_CANCELED') {
        // Mark we handled the abort and remove the pending local message
        lastAbortRef.current = false;
        setLocalMessages([]);
        return;
      }

      console.error("Failed to send message:", error);

      const errorMessage = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content:
          "Sorry, there was an error processing your request. Please try again.",
        message_type: "text",
        timestamp: formatDistanceToNow(new Date(), { addSuffix: true }),
      };

      setLocalMessages((prev) => [...prev, errorMessage]);
    },
  });

  // Create chat mutation
  const createChatMutation = useCreateChat();

  // Convert API messages to UI format and merge with local state
  const messages = useMemo(() => {
    // Convert API messages to UI format
    const apiMessages = chatData?.messages
      ? chatData.messages.map((msg) => ({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          message_type: msg.message_type,
          s3_url: msg.s3_url,
          tool: msg.message_type !== "text" ? msg.message_type : null,
          image: msg.s3_url || null,
          timestamp: formatDistanceToNow(new Date(msg.created_at), {
            addSuffix: true,
          }),
        }))
      : [];

    if (localMessages.length > 0) {
      return [...apiMessages, ...localMessages];
    }

    return apiMessages;
  }, [
    chatData?.messages,
    localMessages,
    sendMessageMutation.isPending,
    createChatMutation.isPending,
  ]);

  const handleSendMessage = async (message) => {
    if (
      !message.trim() ||
      sendMessageMutation.isPending ||
      createChatMutation.isPending
    )
      return;

    // If no chatId, create a new chat first
    if (!chatId) {
      try {
        // Create new chat using the mutation hook
        const chatData = await createChatMutation.mutateAsync({
          title: message,
        });

        const newChatId = chatData.data.chat_id;

        // Navigate to the new chat
        navigate(`/chat/${newChatId}`);

        // Add user message to local state
        const userMessage = {
          id: `user-${Date.now()}`,
          role: "user",
          content: message,
          message_type: "text",
          timestamp: formatDistanceToNow(new Date(), { addSuffix: true }),
        };

        setLocalMessages([userMessage]);

        // Send the message to the new chat using the mutation
        sendMessageMutation.mutate({
          chatId: newChatId,
          data: {
            message,
            conversation_history: [userMessage].map((msg) => ({
              role: msg.role,
              content: msg.content,
            })),
          },
        });
      } catch (error) {
        console.error("Error creating chat or sending message:", error);
        // Add error message to local state
        const errorMessage = {
          id: `error-${Date.now()}`,
          role: "assistant",
          content:
            "Sorry, there was an error creating a new chat. Please try again.",
          message_type: "text",
          timestamp: formatDistanceToNow(new Date(), { addSuffix: true }),
        };

        setLocalMessages((prev) => [...prev, errorMessage]);
      }
    } else {
      // Chat exists, send message normally
      try {
        // Add user message to local state immediately
        const userMessage = {
          id: `user-${Date.now()}`,
          role: "user",
          content: message,
          message_type: "text",
          timestamp: formatDistanceToNow(new Date(), { addSuffix: true }),
        };

        setLocalMessages((prev) => [...prev, userMessage]);

        const history = messages.slice(-5).map((msg) => ({
          role: msg.role,
          content: msg.content,
        }));

        // Send message using the mutation
        sendMessageMutation.mutate({
          chatId: chatId,
          data: {
            message,
            conversation_history: history,
          },
        });
      } catch (error) {
        console.error("Error sending message:", error);

        // Add error message to local state
        const errorMessage = {
          id: `error-${Date.now()}`,
          role: "assistant",
          content:
            "Sorry, there was an error processing your request. Please try again.",
          message_type: "text",
          timestamp: formatDistanceToNow(new Date(), { addSuffix: true }),
        };

        setLocalMessages((prev) => [...prev, errorMessage]);
      }
    }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      // Mark that we intentionally aborted this request so handlers can ignore it
      lastAbortRef.current = true;
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    // Don't call reset() as it can trigger onSuccess callbacks or side-effects
    // The mutation will settle into an error state and our handlers will ignore it
  };

  const isLoading =
    sendMessageMutation.isPending ||
    createChatMutation.isPending ||
    chatLoading;
  const nowLabel = new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date());
  const headerTitle = chatData?.title || "";

  // Show welcome message when no chat is selected
  return (
    <div className="flex h-full min-h-0 flex-col bg-transparent">
      <div className="border-b border-border/70 bg-card/80 px-6 py-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-1">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Today {nowLabel}
            </p>
            <div>
              <h1 className="text-xl font-semibold text-foreground line-clamp-2">
                {headerTitle}
              </h1>
            </div>
          </div>

          <div className="flex w-full items-center gap-3 lg:w-auto">
            <Button
              onClick={() => navigate("/chat")}
              className="rounded-full bg-primary px-4 text-primary-foreground shadow-lg shadow-primary/20"
            >
              <PlusIcon className="mr-2 h-4 w-4" />
              New chat
            </Button>
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-hidden">
        {!chatId ? (
          <div className="flex h-full flex-col">
            <div className="flex flex-1 items-center justify-center px-6">
              <div className="text-center max-w-lg mx-auto space-y-3">
                <h1 className="text-2xl font-bold text-foreground">
                  Welcome to Brandmate
                </h1>
                <p className="text-muted-foreground">
                  Start a new conversation by typing a message below.
                </p>
              </div>
            </div>
            <ChatInput
              onSendMessage={handleSendMessage}
              isLoading={isLoading}
              onStop={handleStop}
              placeholder="Type your message to start a new conversation..."
            />
          </div>
        ) : (
          <div className="flex h-full flex-col">
            <div className="flex-1 min-h-0 overflow-hidden">
              <ChatArea messages={messages} isLoading={isLoading} />
            </div>
            <ChatInput
              onSendMessage={handleSendMessage}
              isLoading={isLoading}
              onStop={handleStop}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default Chat;
