import Credentials from "next-auth/providers/credentials";
import { CredentialsSignin } from "next-auth";
import { authenticateWithCredentials } from "@/lib/api/auth/login";

export const credentialsProvider = Credentials({
  id: "credentials",
  name: "Credentials",
  credentials: {
    email: { label: "Email", type: "email" },
    password: { label: "Password", type: "password" },
    captcha: { label: "Captcha", type: "text" },
  },
  async authorize(credentials, request) {
    if (!credentials?.email || !credentials?.password) return null;

    try {
      const data = await authenticateWithCredentials(
        String(credentials.email),
        String(credentials.password),
        String(credentials.captcha ?? ""),
        request.headers.get("x-forwarded-for")
      );

      return {
        id: data.user.id,
        name: `${data.user.first_name} ${data.user.last_name}`,
        email: data.user.email,
        image: data.user.avatar_url ?? null,
        accessToken: data.access,
        refreshToken: data.refresh,
        role: data.user.role,
      };
    } catch (err) {
      const code = (err as { code?: string } | undefined)?.code;
      if (code === "unverified_email" || code === "inactive" || code === "captcha" || code === "too_many_attempts") {
        const error = new CredentialsSignin();
        error.code = code;
        throw error;
      }
      return null;
    }
  },
});