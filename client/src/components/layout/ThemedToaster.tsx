"use client";

import { useTheme } from "next-themes";
import { Toaster } from "sonner";

export default function ThemedToaster() {
  const { resolvedTheme } = useTheme();
  return (
    <Toaster
      position="top-center"
      richColors
      theme={resolvedTheme === "dark" ? "dark" : "light"}
      toastOptions={{ style: { fontFamily: "var(--font-inter)" } }}
    />
  );
}
