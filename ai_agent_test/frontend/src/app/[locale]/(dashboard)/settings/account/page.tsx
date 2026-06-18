"use client";

import { useState } from "react";
import { AlertTriangle, Lock } from "lucide-react";
import { toast } from "sonner";

import { SettingsSection } from "@/components/settings/settings-section";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
  Button,
  Input,
  Label,
} from "@/components/ui";
import { useAuth } from "@/hooks";
import { apiClient, ApiError } from "@/lib/api-client";

export default function AccountSettingsPage() {
  const { user, logout } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleChangePassword = async () => {
    if (newPassword.length < 8) {
      toast.error("New password must be at least 8 characters");
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }
    setSaving(true);
    try {
      await apiClient.post("/auth/password/change", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      toast.success("Password updated");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      // Backend may not have this endpoint yet — surface a helpful message.
      if (err instanceof ApiError && err.status === 404) {
        toast.error("Password change requires backend wiring (POST /auth/password/change).");
      } else {
        toast.error(err instanceof ApiError ? err.message : "Failed to update password");
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!user) return;
    setDeleting(true);
    try {
      await apiClient.delete(`/users/${user.id}`);
      toast.success("Account deleted");
      logout();
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        toast.error("Self-delete not enabled. Contact support.");
      } else {
        toast.error(err instanceof ApiError ? err.message : "Failed to delete account");
      }
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      <SettingsSection
        title="Change password"
        description="Use a strong, unique password — 8+ characters, mixed case, numbers."
        action={
          <Button
            onClick={handleChangePassword}
            disabled={saving || !currentPassword || !newPassword}
            size="sm"
            className="rounded-full"
          >
            {saving ? "Saving…" : "Update password"}
          </Button>
        }
      >
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label
              htmlFor="current-pw"
              className="text-foreground/80 text-xs font-medium tracking-wider uppercase"
            >
              Current password
            </Label>
            <Input
              id="current-pw"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              autoComplete="current-password"
              className="h-10 rounded-xl"
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label
                htmlFor="new-pw"
                className="text-foreground/80 text-xs font-medium tracking-wider uppercase"
              >
                New password
              </Label>
              <Input
                id="new-pw"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
                className="h-10 rounded-xl"
              />
            </div>
            <div className="space-y-1.5">
              <Label
                htmlFor="confirm-pw"
                className="text-foreground/80 text-xs font-medium tracking-wider uppercase"
              >
                Confirm new password
              </Label>
              <Input
                id="confirm-pw"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
                className="h-10 rounded-xl"
              />
            </div>
          </div>
        </div>
      </SettingsSection>

      <SettingsSection
        title="Sign out everywhere"
        description="Revoke every active session including this one. You'll be signed out immediately."
      >
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="outline" size="sm" className="rounded-full">
              <Lock className="mr-2 h-3.5 w-3.5" />
              Sign out everywhere
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Sign out from all devices?</AlertDialogTitle>
              <AlertDialogDescription>
                This revokes every active session and signs you out of this device too.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={async () => {
                  try {
                    await apiClient.delete("/sessions");
                    toast.success("Signed out from all devices");
                    logout();
                  } catch {
                    toast.error("Failed to sign out everywhere");
                  }
                }}
              >
                Sign out everywhere
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </SettingsSection>

      <SettingsSection
        title="Delete account"
        description="Permanently remove your account, conversations, and uploaded data. This can't be undone."
        danger
      >
        <div className="border-destructive/20 bg-destructive/[0.04] flex items-start gap-3 rounded-xl border p-4">
          <span className="bg-destructive/15 text-destructive flex h-9 w-9 shrink-0 items-center justify-center rounded-xl">
            <AlertTriangle className="h-4 w-4" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-foreground text-sm font-semibold">This is irreversible</p>
            <p className="text-foreground/65 mt-0.5 text-xs leading-relaxed">
              All conversations, knowledge base contents, API keys, and personal data will be
              permanently deleted. Active subscriptions will be canceled.
            </p>
          </div>
        </div>
        <div className="mt-4">
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" size="sm" className="rounded-full">
                Delete my account
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete your account?</AlertDialogTitle>
                <AlertDialogDescription>
                  Your conversations, knowledge base contents, API keys, and all personal data will
                  be permanently deleted. Active subscriptions will be canceled. This cannot be
                  undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  disabled={deleting}
                  onClick={handleDeleteAccount}
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                >
                  {deleting ? "Deleting…" : "Yes, delete my account"}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </SettingsSection>
    </div>
  );
}
