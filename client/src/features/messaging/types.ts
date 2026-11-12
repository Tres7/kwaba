export type MessagingMessage = {
  id: number;
  conversation_id: string;
  sender_id: string;
  content: string;
  created_at: string;
  is_own: boolean;
  /** Contact details hidden when sending (anti-bypass) */
  masked?: boolean;
};

export type MessagingConversation = {
  id: string;
  my_role: "guest" | "host";
  hebergement: {
    id: string;
    name: string;
    city: string;
    image_url: string;
  } | null;
  other_participant: {
    id: string;
    first_name: string;
    last_name: string;
    avatar_url: string | null;
  } | null;
  last_message: MessagingMessage | null;
  unread_count: number;
  last_message_at: string;
  /** The traveller has a paid booking for this listing: otherwise, they stay anonymous to the host */
  booked: boolean;
};

export type ModerationLevel = "allow" | "warn" | "block";

export type ModerationCategory = "insult" | "hate" | "threat" | "harassment";

export type ModerationCheck = {
  level: ModerationLevel;
  categories: ModerationCategory[];
};

export type ReportReason = ModerationCategory | "spam" | "scam" | "other";

export type SanctionStep = "reminder" | "formal_warning" | "short_suspension" | "long_suspension" | "admin_decision";

export type UserSanction = {
  id: number;
  step: SanctionStep;
  category: ReportReason;
  created_at: string;
  ends_at: string | null;
  cancelled: boolean;
  contest_status: "" | "pending" | "accepted" | "rejected";
  contestable: boolean;
};

export type ModerationStatus = {
  suspended_until: string | null;
  sanctions: UserSanction[];
};

export type ReportContextMessage = {
  message_id: number;
  from_author: boolean;
  content: string;
  created_at: string;
  reported: boolean;
};

export type AdminPerson = { id: string; nom: string; email: string };

export type AdminReport = {
  id: number;
  conversation_id: string;
  message_id: number;
  reason: ReportReason;
  details: string;
  status: "pending" | "confirmed" | "rejected";
  created_at: string;
  message_created_at: string;
  reviewed_at: string | null;
  review_note: string;
  legal_hold: boolean;
  context: ReportContextMessage[];
  reporter: AdminPerson;
  author: AdminPerson;
};

export type AdminSanction = {
  id: number;
  user_id: string;
  report_id: number;
  step: SanctionStep;
  category: ReportReason;
  created_at: string;
  starts_at: string | null;
  ends_at: string | null;
  cancelled_at: string | null;
  contested_at: string | null;
  contest_text: string;
  contest_status: UserSanction["contest_status"];
  contest_note: string;
  user?: AdminPerson;
};
