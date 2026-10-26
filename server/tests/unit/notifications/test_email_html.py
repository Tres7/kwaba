from apps.notifications.infrastructure.email.html import CID_LOGO, corps_html, page_html


def test_logo_joint_et_pied_de_page(settings):
    settings.EMAIL_REPLY_TO = 'info@kwa-ba.com'
    page = page_html('Bonjour Ama,\n\nBienvenue.\n\nL\'équipe Kwa-Ba', 'Bienvenue')
    assert f'src="cid:{CID_LOGO}"' in page and 'alt="KWA-BA"' in page
    assert 'mailto:info@kwa-ba.com' in page


def test_code_details_et_boutons():
    html = corps_html(
        "Votre code est :\n\n    482915\n\n"
        "  Référence : RES-1\n  Du 20 au 25 novembre\n\n"
        "Pour lire la conversation et répondre :\nhttps://kwa-ba.com/messages/1\n\n"
        "Voir la réservation : https://kwa-ba.com/r/1"
    )
    assert 'letter-spacing:10px' in html and '482915' in html          # highlighted code
    assert '>Référence</td>' in html and '>RES-1</td>' in html          # details card
    assert 'href="https://kwa-ba.com/messages/1"' in html and '>Pour lire la conversation et répondre</a>' in html
    assert '>Voir la réservation</a>' in html


def test_contenu_echappe():
    html = corps_html('Message : <script>alert(1)</script>')
    assert '<script>' not in html and '&lt;script&gt;' in html
