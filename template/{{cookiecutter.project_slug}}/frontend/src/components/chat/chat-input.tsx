"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Button, Badge } from "@/components/ui";
import { Send, Loader2, Mic, MicOff, Paperclip, X } from "lucide-react";
import { toast } from "sonner";

interface AttachedFile {
  name: string;
  content: string;
}

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  isProcessing?: boolean;
}

export function ChatInput({ onSend, disabled, isProcessing }: ChatInputProps) {
  const [message, setMessage] = useState("");
  const [attachedFile, setAttachedFile] = useState<AttachedFile | null>(null);
  const [isListening, setIsListening] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  useEffect(() => {
    if (!isProcessing && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isProcessing]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [message]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = message.trim();
    if (!trimmed && !attachedFile) return;
    if (disabled) return;

    let fullMessage = trimmed;

    if (attachedFile) {
      const fileContext = `\n\n---\nAttached file: ${attachedFile.name}\n\`\`\`\n${attachedFile.content}\n\`\`\``;
      fullMessage = trimmed ? trimmed + fileContext : `Please analyze this file: ${attachedFile.name}` + fileContext;
      setAttachedFile(null);
    }

    onSend(fullMessage);
    setMessage("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const toggleMic = useCallback(() => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      toast.info("Voice input is only supported in Chrome. Use Chrome for speech-to-text.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = navigator.language || "en-US";

    let finalTranscript = "";

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }
      setMessage(() => {
        return finalTranscript + (interim ? "\u200B" + interim : "");
      });
    };

    recognition.onend = () => {
      setIsListening(false);
      setMessage((prev) => prev.replace(/\u200B/g, ""));
    };

    recognition.onerror = () => {
      setIsListening(false);
      toast.error("Speech recognition error");
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
    finalTranscript = message;
  }, [isListening, message]);

  const handleFileSelect = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      e.target.value = "";

      const textExtensions = [".txt", ".md", ".csv", ".json", ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".yaml", ".yml", ".toml", ".xml", ".sql", ".sh", ".env"];
      const isTextFile = textExtensions.some((ext) =>
        file.name.toLowerCase().endsWith(ext)
      );

      if (!isTextFile) {
        toast.info("Only text files can be attached. Image and PDF support coming soon.");
        return;
      }

      if (file.size > 100_000) {
        toast.error("File too large. Maximum 100KB for text attachments.");
        return;
      }

      try {
        const content = await file.text();
        setAttachedFile({ name: file.name, content });
      } catch {
        toast.error("Failed to read file");
      }
    },
    []
  );

  return (
    <form onSubmit={handleSubmit}>
      {attachedFile && (
        <div className="flex items-center gap-2 pb-2">
          <Badge variant="secondary" className="gap-1.5 pr-1">
            <Paperclip className="h-3 w-3" />
            <span className="max-w-[200px] truncate text-xs">
              {attachedFile.name}
            </span>
            <button
              type="button"
              onClick={() => setAttachedFile(null)}
              className="hover:bg-muted ml-0.5 rounded p-0.5"
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        </div>
      )}

      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          disabled={disabled}
          rows={1}
          className="placeholder:text-muted-foreground min-h-[40px] flex-1 resize-none bg-transparent py-2.5 text-sm focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 sm:text-base"
        />

        <div className="flex shrink-0 items-center gap-0.5 pb-1">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={toggleMic}
            disabled={disabled}
            className="h-9 w-9"
            title={isListening ? "Stop recording" : "Voice input"}
          >
            {isListening ? (
              <MicOff className="h-4 w-4 animate-pulse text-red-500" />
            ) : (
              <Mic className="text-muted-foreground h-4 w-4" />
            )}
          </Button>

          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            className="h-9 w-9"
            title="Attach file"
          >
            <Paperclip className="text-muted-foreground h-4 w-4" />
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileSelect}
            accept=".txt,.md,.csv,.json,.py,.js,.ts,.tsx,.html,.css,.yaml,.yml,.toml,.xml,.sql,.sh"
            className="hidden"
          />

          <Button
            type="submit"
            size="icon"
            disabled={disabled || (!message.trim() && !attachedFile)}
            className="h-9 w-9 rounded-lg"
          >
            {isProcessing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            <span className="sr-only">Send message</span>
          </Button>
        </div>
      </div>
    </form>
  );
}
