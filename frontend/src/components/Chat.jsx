import React, { useMemo, useState, useRef, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ChatArea } from "./ChatArea";
import { ChatInput } from "./ChatInput";
import { formatDistanceToNow } from "date-fns";
import { useChat, useCreateChat } from "../hooks/useChat";
import { api } from "../services/api";
import { MESSAGE_TYPE_TEXT, MESSAGE_TYPE_WEBSITE } from "../constants/toolTypes";
import { queryKeys } from "../types/api";

// How fast to reveal text: characters per tick, tick interval in ms
const CHARS_PER_TICK = 6;
const TICK_MS = 16; // ~60 fps

const Chat = () => {
  const { chatId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [localMessages, setLocalMessages] = useState([]);
  const [welcomed, setWelcomed] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const abortControllerRef = useRef(null);
  const typewriterRef = useRef(null);
  const prevChatIdRef = useRef(chatId);
  const geoCoordsRef = useRef(null);

  const isNearMeQuery = useCallback((text) => {
    if (!text) return false;
    return /\b(near\s+me|near\s+my\s+location|close\s+to\s+me|around\s+me|nearby|my\s+location|current\s+location)\b/i.test(text);
  }, []);

  const getCurrentCoordinatesFromBrowser = useCallback(async () => {
    if (geoCoordsRef.current) return geoCoordsRef.current;
    if (!navigator.geolocation) return null;

    try {
      const position = await new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 5000,
          maximumAge: 300000,
        });
      });

      const coords = {
        lat: Number(position.coords.latitude),
        lon: Number(position.coords.longitude),
      };
      geoCoordsRef.current = coords;
      return coords;
    } catch (error) {
      console.warn("Could not determine current coordinates from browser location:", error);
      return null;
    }
  }, []);

  useEffect(() => {
    if (typewriterRef.current) {
      clearInterval(typewriterRef.current);
      typewriterRef.current = null;
    }
    const prev = prevChatIdRef.current;
    prevChatIdRef.current = chatId;

    if (prev && prev !== chatId) {
      queryClient.invalidateQueries({ queryKey: queryKeys.chat(prev) });
    }

    const fromWelcomeToNewChat = prev === undefined && chatId !== undefined;
    if (!fromWelcomeToNewChat) {
      setLocalMessages([]);
    }
    setIsTyping(false);
    if (!chatId) setWelcomed(false);
  }, [chatId, queryClient]);

  useEffect(() => {
    return () => {
      if (typewriterRef.current) clearInterval(typewriterRef.current);
    };
  }, []);

  const { data: chatData, isLoading: chatLoading } = useChat(chatId);

  const runTypewriter = useCallback((msgId, fullText, image, html, tool) => {
    setIsTyping(true);
    let pos = 0;

    typewriterRef.current = setInterval(() => {
      pos = Math.min(pos + CHARS_PER_TICK, fullText.length);
      const done = pos >= fullText.length;

      setLocalMessages((prev) =>
        prev.map((msg) =>
          msg.id === msgId
            ? {
                ...msg,
                content: fullText.slice(0, pos),
                // Reveal image/html/tool only once text is fully shown
                ...(done ? { image: image || null, html: html || null, tool: tool || null } : {}),
              }
            : msg
        )
      );

      if (done) {
        clearInterval(typewriterRef.current);
        typewriterRef.current = null;
        setIsTyping(false);
      }
    }, TICK_MS);
  }, []);

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: ({ chatId, data }) => {
      abortControllerRef.current = new AbortController();
      return api.sendMessage(chatId, data, abortControllerRef.current.signal);
    },
    onSuccess: (response) => {
      abortControllerRef.current = null;
      const { message, image, html, tool } = response.data;
      const msgId = `assistant-${Date.now()}`;

      // Add placeholder with empty content, then typewrite into it
      setLocalMessages((prev) => [
        ...prev,
        {
          id: msgId,
          role: "assistant",
          content: "",
          message_type: MESSAGE_TYPE_TEXT,
          image: null,
          html: null,
          tool: null,
          timestamp: formatDistanceToNow(new Date(), { addSuffix: true }),
        },
      ]);

      runTypewriter(msgId, message, image, html, tool);
    },
    onError: (error) => {
      abortControllerRef.current = null;
      if (error.name === "CanceledError" || error.code === "ERR_CANCELED") return;

      console.error("Failed to send message:", error);
      setLocalMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: "assistant",
          content: "Sorry, there was an error processing your request. Please try again.",
          message_type: MESSAGE_TYPE_TEXT,
          timestamp: formatDistanceToNow(new Date(), { addSuffix: true }),
        },
      ]);
    },
  });

  const createChatMutation = useCreateChat();

  const messages = useMemo(() => {
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
          timestamp: formatDistanceToNow(new Date(msg.created_at), { addSuffix: true }),
        }))
      : [];

    return localMessages.length > 0 ? [...apiMessages, ...localMessages] : apiMessages;
  }, [chatData?.messages, localMessages]);

  const buildPayload = async (message, imageFile, conversationHistory) => {
    let image_base64 = null;
    let current_city = null;
    let current_lat = null;
    let current_lon = null;

    if (imageFile) {
      image_base64 = await new Promise((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result.split(",")[1]);
        reader.readAsDataURL(imageFile);
      });
    }

    if (isNearMeQuery(message)) {
      const coords = await getCurrentCoordinatesFromBrowser();
      if (coords) {
        current_lat = coords.lat;
        current_lon = coords.lon;
      }
    }

    return {
      message,
      conversation_history: conversationHistory,
      image_base64,
      current_city,
      current_lat,
      current_lon,
    };
  };

  const handleSendMessage = async (message, imageFile = null) => {
    if (
      (!message.trim() && !imageFile) ||
      sendMessageMutation.isPending ||
      createChatMutation.isPending
    )
      return;

    if (!chatId) {
      setWelcomed(true);
      try {
        const chatData = await createChatMutation.mutateAsync({ title: message });
        const newChatId = chatData.data.chat_id;
        navigate(`/chat/${newChatId}`);

        const userMessage = {
          id: `user-${Date.now()}`,
          role: "user",
          content: message,
          message_type: MESSAGE_TYPE_TEXT,
          image: imageFile ? URL.createObjectURL(imageFile) : null,
          timestamp: formatDistanceToNow(new Date(), { addSuffix: true }),
        };
        setLocalMessages([userMessage]);

        sendMessageMutation.mutate({
          chatId: newChatId,
          data: await buildPayload(message, imageFile, [
            { role: userMessage.role, content: userMessage.content },
          ]),
        });
      } catch (error) {
        console.error("Error creating chat:", error);
        setLocalMessages((prev) => [
          ...prev,
          {
            id: `error-${Date.now()}`,
            role: "assistant",
            content: "Sorry, there was an error creating a new chat. Please try again.",
            message_type: MESSAGE_TYPE_TEXT,
            timestamp: formatDistanceToNow(new Date(), { addSuffix: true }),
          },
        ]);
      }
    } else {
      const userMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: message,
        message_type: MESSAGE_TYPE_TEXT,
        image: imageFile ? URL.createObjectURL(imageFile) : null,
        timestamp: formatDistanceToNow(new Date(), { addSuffix: true }),
      };
      setLocalMessages((prev) => [...prev, userMessage]);

      const history = messages.slice(-5).map((msg) => ({
        role: msg.role,
        content: msg.content,
      }));

      sendMessageMutation.mutate({
        chatId,
        data: await buildPayload(message, imageFile, history),
      });
    }
  };

  const handleStop = () => {
    // Cancel in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    // Stop typewriter mid-animation
    if (typewriterRef.current) {
      clearInterval(typewriterRef.current);
      typewriterRef.current = null;
      setIsTyping(false);
    }
    sendMessageMutation.reset();
  };

  const isPending = sendMessageMutation.isPending || createChatMutation.isPending;
  const isLoading = isPending || isTyping;
  const lastLocal = localMessages[localMessages.length - 1];
  const showTypingIndicator =
    isPending && (lastLocal == null || lastLocal.role === "user");

  const isWelcome = !chatId && !welcomed;

  // Full-area spinner only when the chat query has nothing to show yet. After creating a chat,
  // we already have optimistic local messages — keep showing ChatArea while GET /chats/:id runs.
  const showChatSkeleton = chatLoading && messages.length === 0;

  return (
    <div className="relative flex h-full min-h-0 flex-col overflow-hidden bg-background">
      <div
        className={`flex-1 min-h-0 overflow-hidden transition-opacity duration-300 ${
          isWelcome ? "opacity-0 pointer-events-none" : "opacity-100"
        }`}
      >
        {showChatSkeleton ? (
          <div className="flex h-full items-center justify-center">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : (
          <ChatArea messages={messages} isLoading={showTypingIndicator} />
        )}
      </div>

      <div
        className="transition-transform duration-500 ease-[cubic-bezier(0.33,1,0.68,1)]"
        style={{ transform: isWelcome ? "translateY(calc(-50vh + 85px))" : "translateY(0)" }}
      >
        <div
          className={`overflow-hidden text-center transition-all duration-300 ease-in-out ${
            isWelcome ? "max-h-28 opacity-100 pb-5" : "max-h-0 opacity-0 pb-0"
          }`}
        >
          <h1 className="font-brand text-4xl font-semibold text-foreground/90 select-none tracking-wide">
            What shall we create?
          </h1>
          <p className="mt-1 text-sm text-muted-foreground select-none">
            Your AI partner for Eastern fashion & brand marketing
          </p>
        </div>

        <ChatInput
          onSendMessage={handleSendMessage}
          isLoading={isLoading || showChatSkeleton}
          onStop={handleStop}
          placeholder="Message Brandmate…"
        />
      </div>
    </div>
  );
};

export default Chat;
