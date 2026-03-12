"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui";
import { Send, Loader2, Paperclip } from "lucide-react";
import { isRagEnabled, uploadDocument } from "@/lib/rag-api";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  isProcessing?: boolean;
  collectionName?: string;
}

export function ChatInput({ onSend, disabled, isProcessing, collectionName = "documents" }: ChatInputProps) {
  const [message, setMessage] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const ragEnabled = isRagEnabled();

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
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !ragEnabled) return;

    setIsUploading(true);
    setUploadStatus(null);
    try {
      await uploadDocument(collectionName, file);
      setUploadStatus({ type: "success", message: `Uploaded ${file.name}` });
      // Clear success message after 3 seconds
      setTimeout(() => setUploadStatus(null), 3000);
    } catch (error) {
      console.error("Upload failed:", error);
      setUploadStatus({ type: "error", message: "Failed to upload document" });
      // Clear error message after 5 seconds
      setTimeout(() => setUploadStatus(null), 5000);
    } finally {
      setIsUploading(false);
      // Reset the file input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const openFilePicker = () => {
    fileInputRef.current?.click();
  };

  return (
    <form onSubmit={handleSubmit} className="relative">
      {uploadStatus && (
        <div
          className={cn(
            "absolute bottom-full left-0 mb-2 rounded-md px-3 py-2 text-sm",
            uploadStatus.type === "success"
              ? "bg-green-100 text-green-800"
              : "bg-red-100 text-red-800"
          )}
        >
          {uploadStatus.message}
        </div>
      )}
      <textarea
        ref={textareaRef}
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type a message..."
        disabled={disabled}
        rows={1}
        className="w-full resize-none bg-transparent py-3 pr-28 text-sm sm:text-base placeholder:text-muted-foreground focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
      />
      <div className="absolute right-0 top-0 flex h-10 items-center gap-2">
        {ragEnabled && (
          <>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.md,.txt"
              onChange={handleFileUpload}
              className="hidden"
            />
            <Button
              type="button"
              size="icon"
              variant="ghost"
              disabled={disabled || isUploading}
              onClick={openFilePicker}
              className="h-10 w-10 rounded-lg"
            >
              {isUploading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Paperclip className="h-5 w-5" />
              )}
              <span className="sr-only">Upload document</span>
            </Button>
          </>
        )}
        <Button
          type="submit"
          size="icon"
          disabled={disabled || !message.trim()}
          className="h-10 w-10 rounded-lg"
        >
          {isProcessing ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Send className="h-5 w-5" />
          )}
          <span className="sr-only">Send message</span>
        </Button>
      </div>
    </form>
  );
}
