import { createNavigation } from "next-intl/navigation";
import { routing } from "./routing";

/** To use instead of next/link and next/navigation: links keep the current language (/en/…). */
export const { Link, redirect, usePathname, useRouter, getPathname } = createNavigation(routing);
