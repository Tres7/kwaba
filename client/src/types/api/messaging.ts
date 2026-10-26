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
