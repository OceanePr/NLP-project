import requests
from bs4 import BeautifulSoup
import string
import time


# Sujet médical

liste_vocab_medical = []

url_medical = "https://www.hopital.fr/Le-dico-medical/Les-pathologies-et-symptomes"
response = requests.get(url_medical)
response.raise_for_status()
soup = BeautifulSoup(response.text, "html.parser")

liste_vocab_medical = []

for letter in string.ascii_lowercase:
    section = soup.find("section", class_=f"letter-block-{letter}")
    if not section:
        print(f"❌ Aucune section pour la lettre {letter.upper()}")
        continue

    ul = section.find("ul", class_="nav n2")
    if ul:
        mots = [a.text.strip().lower() for a in ul.find_all("a")]
        liste_vocab_medical.extend(mots)
    else:
        print(f"⚠️ Pas de liste trouvée pour {letter.upper()}")

    time.sleep(0.2)  # pause entre les requêtes


print(f"\n Total de mots récupérés : {len(liste_vocab_medical)}")
for mot in liste_vocab_medical:
    print(mot)
