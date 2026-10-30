import { Link } from "@/i18n/navigation";
import LienContact from "@/components/legal/LienContact";
import FormeSociete from "@/components/legal/FormeSociete";
import MentionSociete from "@/components/legal/MentionSociete";
import LegalPage, { AC, VersionFrancaiseFaitFoi } from "@/components/legal/LegalPage";

/** English version (the French version prevails). */
export default function ContenuEn() {
  return (
    <LegalPage
      titre="Legal notice"
      miseAJour="30 October 2026"
      intro={
        <>
          <p>Information about the publisher of the Kwa-Ba website, its host and the content published on it.</p>
          <VersionFrancaiseFaitFoi />
        </>
      }
      sections={[
        {
          id: "editeur",
          titre: "Website publisher",
          contenu: (
            <ul>
              <li>Company name: <strong>KWA-BA</strong>, <FormeSociete /> with a share capital of 100,000 F CFA</li>
              <li>Registered office: Totsi Gblenkomé district, street 243, Lomé (Togo)</li>
              <li>Registration: Lomé RCCM no. <MentionSociete cle="rccm" libelle="RCCM" />; tax number (NIF) <MentionSociete cle="nif" libelle="NIF" /></li>
              <li>E-commerce: registered as an e-commerce provider under no. <MentionSociete cle="commerce_electronique" libelle="number" /> (decree no. 2018-062/PR)</li>
              <li>Personal data: declaration to the personal data protection authority (IPDCP) no. <MentionSociete cle="ipdcp" libelle="number" /></li>
              <li>Contact: <LienContact />; postal address: Totsi Gblenkomé district, street 243, Lomé, Togo</li>
              <li>President: Mr MENDE Fadel — General Manager: Mr KPOGLO Dzidoula Godwin Trésor — Publication director: Mr MENDE Fadel.</li>
            </ul>
          ),
        },
        {
          id: "hebergeur",
          titre: "Hosting provider",
          contenu: (
            <ul>
              <li>Name: <strong>IONOS SE</strong> (virtual private server of the website and its data)</li>
              <li>Address: Elgendorfer Straße 57, 56410 Montabaur, Germany</li>
              <li>Phone: +49 721 170 5522</li>
              <li>The kwa-ba.com domain name and the info@kwa-ba.com mailbox are managed by Hostinger.</li>
            </ul>
          ),
        },
        {
          id: "paiement",
          titre: "Payment provider",
          contenu: <p>FedaPay, a payment institution licensed by the BCEAO; if needed, another licensed provider (<Link href="/cgv#paiement">terms of sale, art. 7</Link>).</p>,
        },
        {
          id: "propriete",
          titre: "Intellectual property",
          contenu: (
            <p>
              The Kwa-Ba name, logo, graphic charter, texts and code of the Platform belong to KWA-BA, unless stated otherwise{" "}
              <AC>trademark registered with OAPI under no. …, if filed</AC>. Any reproduction without permission is prohibited. Listings, photos and reviews published by users remain the
              property of their authors.
            </p>
          ),
        },
        {
          id: "credits",
          titre: "Credits",
          contenu: (
            <ul>
              <li>Illustration photos for demo listings and sign-in pages: <a href="https://unsplash.com" target="_blank" rel="noopener noreferrer">Unsplash</a>, under the <a href="https://unsplash.com/license" target="_blank" rel="noopener noreferrer">Unsplash licence</a>.</li>
              <li>Home page photos: <a href="https://www.pexels.com" target="_blank" rel="noopener noreferrer">Pexels</a>, under the <a href="https://www.pexels.com/license/" target="_blank" rel="noopener noreferrer">Pexels licence</a> (free use, including commercial, attribution not required):
                <ul>
                  <li>Waterfall and green cliff</li>
                  <li>Safari vehicle in the savanna</li>
                  <li>Elephant in golden grass</li>
                  <li>Elephant family in the savanna</li>
                  <li>Elephant under acacia trees</li>
                  <li>Giraffes in the savanna</li>
                  <li>Aerial view of a jetty and a coastal city</li>
                  <li>Elephant in front of Kilimanjaro</li>
                  <li>Elephants in front of Kilimanjaro</li>
                </ul>
              </li>
              <li>Montserrat and Inter fonts: SIL Open Font License.</li>
              <li>Icons: Lucide (ISC licence) and Phosphor (MIT licence).</li>
              <li>Listing photos: published by hosts, who guarantee they hold the rights.</li>
            </ul>
          ),
        },
        {
          id: "signalement",
          titre: "Report content",
          contenu: (
            <p>
              To report unlawful content (fraudulent listing, photo used without permission, hate speech), write to{" "}
              <LienContact sujet="Content report" /> with the address of the page concerned. Clearly unlawful content is removed as
              quickly as possible.
            </p>
          ),
        },
      ]}
    />
  );
}
