import { redirect } from "next/navigation";

import { ROUTES } from "@/lib/constants";

export default function SettingsIndex() {
  redirect(ROUTES.SETTINGS_PROFILE);
}
