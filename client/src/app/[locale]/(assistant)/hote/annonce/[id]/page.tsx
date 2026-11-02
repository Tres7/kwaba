"use client";

import { Suspense, use } from "react";
import AssistantHote from "@/features/hebergements/assistant/AssistantHote";

export default function AssistantHotePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return (
    <Suspense fallback={<div className="min-h-dvh bg-light-muted" />}>
      <AssistantHote id={id} />
    </Suspense>
  );
}
