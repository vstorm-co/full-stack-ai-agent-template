"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Button, Badge, Spinner } from "@/components/ui";
import { Send, Mic, MicOff, Paperclip, X, Image as ImageIcon, FileText } from "lucide-react";
import Image from "next/image";
import { toast } from "sonner";
import { uploadFile, getFileUrl, type FileUploadResponse } from "@/lib/file-api";

interface ChatInputProps {
  onSend: (message: string, fileIds?: string[]) => void;
  disabled?: boolean;
  isProcessing?: boolean;
}

export function ChatInput({ onSend, disabled, isProcessing }: ChatInputProps) {
  const [message, setMessage] = useState("");
  const [attachedFiles, setAttachedFiles] = useState<FileUploadResponse[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  useEffect(() => {
    if (!isProcessing && !isUploading && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isProcessing, isUploading]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [message]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = message.trim();
    if (!trimmed && attachedFiles.length === 0) return;
    if (disabled || isUploading) return;

    const fileIds = attachedFiles.length > 0 ? attachedFiles.map((f) => f.id) : undefined;
    onSend(trimmed || "Analyze the attached file(s)", fileIds);
    setMessage("");
    setAttachedFiles([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Speech recognition
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
        if (!result) continue;
        if (result.isFinal) {
          finalTranscript += result[0]?.transcript ?? "";
        } else {
          interim += result[0]?.transcript ?? "";
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

  // File upload to backend
  const handleFileSelect = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (!files || files.length === 0) return;
      e.target.value = "";

      const maxMb = parseInt(process.env.NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB || "50", 10);
      for (const file of Array.from(files)) {
        if (file.size > maxMb * 1024 * 1024) {
          toast.error(`${file.name}: File too large. Maximum ${maxMb}MB.`);
          continue;
        }

        setIsUploading(true);
        try {
          const result = await uploadFile(file);
          setAttachedFiles((prev) => [...prev, result]);
        } catch (err) {
          const msg = err instanceof Error ? err.message : "Upload failed";
          toast.error(`${file.name}: ${msg}`);
        } finally {
          setIsUploading(false);
        }
      }
    },
    []
  );

  const removeFile = (fileId: string) => {
    setAttachedFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Attached files */}
      {attachedFiles.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 pb-2">
          {attachedFiles.map((file) => (
            <div key={file.id} className="relative">
              {file.file_type === "image" ? (
                <div className="group relative h-16 w-16 overflow-hidden rounded-lg border">
                  <Image
                    src={getFileUrl(file.id)}
                    alt={file.filename}
                    fill
                    className="object-cover"
                    unoptimized
                  />
                  <button
                    type="button"
                    onClick={() => removeFile(file.id)}
                    className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-destructive-foreground opacity-0 transition-opacity group-hover:opacity-100"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ) : (
                <Badge variant="secondary" className="gap-1.5 pr-1">
                  <FileText className="h-3 w-3" />
                  <span className="max-w-[150px] truncate text-xs">
                    {file.filename}
                  </span>
                  <button
                    type="button"
                    onClick={() => removeFile(file.id)}
                    className="hover:bg-muted ml-0.5 rounded p-0.5"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              )}
            </div>
          ))}
          {isUploading && (
            <div className="flex h-16 w-16 items-center justify-center rounded-lg border border-dashed">
              <Spinner className="text-muted-foreground h-5 w-5" />
            </div>
          )}
        </div>
      )}

      {/* Input row */}
      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          disabled={disabled}
          rows={1}
          className="scrollbar-thin placeholder:text-muted-foreground min-h-[40px] flex-1 resize-none bg-transparent py-2.5 text-sm focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 sm:text-base"
        />

        <div className="flex shrink-0 items-center gap-0.5 pb-1">
          {/* Microphone */}
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

          {/* File attachment */}
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || isUploading}
            className="h-9 w-9"
            title="Attach file"
          >
            {isUploading ? (
              <Spinner className="text-muted-foreground h-4 w-4" />
            ) : (
              <Paperclip className="text-muted-foreground h-4 w-4" />
            )}
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileSelect}
            accept="image/jpeg,image/png,image/gif,image/webp,.txt,.md,.csv,.json,.py,.js,.ts,.tsx,.html,.css,.yaml,.yml,.toml,.xml,.sql,.sh,.pdf,.docx"
            multiple
            className="hidden"
          />

          {/* Send */}
          <Button
            type="submit"
            size="icon"
            disabled={disabled || isUploading || (!message.trim() && attachedFiles.length === 0)}
            className="h-9 w-9 rounded-lg"
          >
            {isProcessing ? (
              <Spinner className="h-4 w-4" />
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
