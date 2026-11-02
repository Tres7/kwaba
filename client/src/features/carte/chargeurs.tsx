"use client";

import dynamic from "next/dynamic";

// The map library is heavy: it only loads on the pages that show a map, once they are on screen
const Attente = () => <div className="w-full h-full skeleton" />;

export const CarteResultats = dynamic(() => import("./CarteResultats"), { ssr: false, loading: Attente });
export const CarteLogement = dynamic(() => import("./CarteLogement"), { ssr: false, loading: Attente });
export const ChoixPosition = dynamic(() => import("./ChoixPosition"), { ssr: false, loading: Attente });
