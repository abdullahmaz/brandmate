import React, { useMemo, useState, useRef, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ChatArea } from "./ChatArea";
import { ChatInput } from "./ChatInput";
import { formatDistanceToNow } from "date-fns";
import { useChat, useCreateChat } from "../hooks/useChat";
import { api } from "../services/api";
import { queryKeys } from "../types/api";
import { MESSAGE_TYPE_TEXT, MESSAGE_TYPE_WEBSITE } from "../constants/toolTypes";

const Chat = () => {
  const { chatId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [localMessages, setLocalMessages] = useState([]);
  const [welcomed, setWelcomed] = useState(false); // true once first message is sent
  const abortControllerRef = useRef(null);

  // Reset welcomed state when navigating to a fresh /chat page
  useEffect(() => {
    if (!chatId) setWelcomed(false);
  }, [chatId]);

  // Only load chat data if we have a chatId and no local messages
  const { data: chatData, isLoading: chatLoading } = useChat(chatId);

  // Send message mutation with custom onSuccess handler
  const sendMessageMutation = useMutation({
    mutationFn: ({ chatId, data }) => {
      // Create a new AbortController for this request
      abortControllerRef.current = new AbortController();
      return api.sendMessage(chatId, data, abortControllerRef.current.signal);
    },
    onSuccess: (response, variables) => {
      const { chatId } = variables;

      // Clear AbortController
      abortControllerRef.current = null;

      // Videos and images are now stored in S3 — always refresh from DB
      setLocalMessages([]);
      if (chatId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.chat(chatId) });
      }
    },
    onError: (error) => {
      // Clear AbortController
      abortControllerRef.current = null;

      // Don't show error message if request was aborted
      if (error.name === 'CanceledError' || error.code === 'ERR_CANCELED') {
        return;
      }

      console.error("Failed to send message:", error);

      const errorMessage = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content:
          "Sorry, there was an error processing your request. Please try again.",
        message_type: MESSAGE_TYPE_TEXT,
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
          metadata: msg.metadata,
          tool: msg.message_type !== MESSAGE_TYPE_TEXT ? msg.message_type : null,
          image: msg.s3_url || null,
          html: msg.message_type === MESSAGE_TYPE_WEBSITE ? (msg.metadata?.html ?? null) : null,
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

  // --- IMAGE HELPER (new) ---
  // Converts image to base64 if present, then sends plain JSON (same as original).
  const buildPayload = async (message, imageFile, conversationHistory) => {
    let image_base64 = null;
    if (imageFile) {
      image_base64 = await new Promise((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result.split(",")[1]);
        reader.readAsDataURL(imageFile);
      });
    }
    return { message, conversation_history: conversationHistory, image_base64 };
  };

  const handleSendMessage = async (message, imageFile = null) => {
    if (
      (!message.trim() && !imageFile) ||
      sendMessageMutation.isPending ||
      createChatMutation.isPending
    )
      return;

    // If no chatId, create a new chat first
    if (!chatId) {
      setWelcomed(true); // trigger slide-down animation immediately
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
          message_type: MESSAGE_TYPE_TEXT,
          image: imageFile ? URL.createObjectURL(imageFile) : null, // local preview
          timestamp: formatDistanceToNow(new Date(), { addSuffix: true }),
        };

        setLocalMessages([userMessage]);

        // Send the message to the new chat using the mutation
        sendMessageMutation.mutate({
          chatId: newChatId,
          data: await buildPayload(message, imageFile, [userMessage].map((msg) => ({
            role: msg.role,
            content: msg.content,
          }))),
        });
      } catch (error) {
        console.error("Error creating chat or sending message:", error);
        // Add error message to local state
        const errorMessage = {
          id: `error-${Date.now()}`,
          role: "assistant",
          content:
            "Sorry, there was an error creating a new chat. Please try again.",
          message_type: MESSAGE_TYPE_TEXT,
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
          message_type: MESSAGE_TYPE_TEXT,
          image: imageFile ? URL.createObjectURL(imageFile) : null, // local preview
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
          data: await buildPayload(message, imageFile, history),
        });
      } catch (error) {
        console.error("Error sending message:", error);

        // Add error message to local state
        const errorMessage = {
          id: `error-${Date.now()}`,
          role: "assistant",
          content:
            "Sorry, there was an error processing your request. Please try again.",
          message_type: MESSAGE_TYPE_TEXT,
          timestamp: formatDistanceToNow(new Date(), { addSuffix: true }),
        };

        setLocalMessages((prev) => [...prev, errorMessage]);
      }
    }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    sendMessageMutation.reset();
  };

  const isLoading =
    sendMessageMutation.isPending ||
    createChatMutation.isPending ||
    chatLoading;

  const isWelcome = !chatId && !welcomed;

  return (
    <div className="relative flex h-full min-h-0 flex-col overflow-hidden bg-background">
      {/* Messages — hidden (not removed) on welcome so layout is stable */}
      <div
        className={`flex-1 min-h-0 overflow-hidden transition-opacity duration-300 ${
          isWelcome ? 'opacity-0 pointer-events-none' : 'opacity-100'
        }`}
      >
        <ChatArea messages={messages} isLoading={isLoading} />
      </div>

      {/* Bottom panel: heading + input.
          In welcome mode the whole panel is translated upward so it appears
          vertically centered. On first send it transitions back to y=0. */}
      <div
        className="transition-transform duration-500 ease-[cubic-bezier(0.33,1,0.68,1)]"
        style={{ transform: isWelcome ? 'translateY(calc(-50vh + 85px))' : 'translateY(0)' }}
      >
        {/* Welcome heading — fades out once welcomed */}
        <div
          className={`overflow-hidden text-center transition-all duration-300 ease-in-out ${
            isWelcome ? 'max-h-16 opacity-100 pb-5' : 'max-h-0 opacity-0 pb-0'
          }`}
        >
          <h1 className="text-2xl font-semibold text-foreground/80 select-none">
            What can I help with?
          </h1>
        </div>

        <ChatInput
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          onStop={handleStop}
          placeholder="Message Brandmate…"
        />
      </div>
    </div>
  );
};

export default Chat;