"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import IconeKwaba from "@/components/layout/IconeKwaba";
import { Logotype } from "@/components/layout/Logo";
import { useTranslations } from "next-intl";

// Display time: just enough to see the brand (user feedback: 4.5 s was too long).
// A click, a key or a touch skips it.
const DUREE_MS = 2000;

export default function SplashScreen() {
  const t = useTranslations("commun");
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const shown = sessionStorage.getItem("splash_shown");
    if (!shown) {
      setVisible(true);
      sessionStorage.setItem("splash_shown", "1");
      const t = setTimeout(() => setVisible(false), DUREE_MS);
      const passer = () => setVisible(false);
      window.addEventListener("keydown", passer, { once: true });
      return () => {
        clearTimeout(t);
        window.removeEventListener("keydown", passer);
      };
    }
  }, []);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="splash"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, scale: 1.05 }}
          transition={{ duration: 0.3, ease: "easeInOut" }}
          onClick={() => setVisible(false)}
          className="fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-white dark:bg-[#0f172a] cursor-pointer"
        >
          {/* Animated logo */}
          <motion.div
            initial={{ scale: 0.6, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.4, ease: "backOut" }}
            className="flex flex-col items-center gap-4"
          >
            {/* Pictogramme */}
            <motion.div initial={{ y: 8 }} animate={{ y: 0 }} transition={{ delay: 0.15, duration: 0.35, ease: "easeOut" }}>
              <IconeKwaba taille={76} className="rounded-[18px] shadow-card" />
            </motion.div>

            {/* Logotype */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25, duration: 0.3 }}
            >
              <Logotype className="text-4xl" />
            </motion.div>

            {/* Tagline */}
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4, duration: 0.3 }}
              className="text-sm text-gray-600 dark:text-slate-300 font-body tracking-[0.18em]"
            >
              {t("slogan")}
            </motion.p>
          </motion.div>

          {/* Barre de chargement */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2, duration: 0.2 }}
            className="absolute bottom-16 w-40 h-1 bg-gray-100 rounded-full overflow-hidden"
          >
            <motion.div
              initial={{ width: "0%" }}
              animate={{ width: "100%" }}
              transition={{ delay: 0.2, duration: DUREE_MS / 1000 - 0.45, ease: "easeOut" }}
              className="h-full rounded-full"
              style={{ background: "linear-gradient(90deg, #0E4D47, #F59E0B)" }}
            />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
