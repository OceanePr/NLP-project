import requests
from bs4 import BeautifulSoup
import string
import time
import spacy
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# Sujet médical

def get_medical_terms():
    
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
        mots += ["vaccination", "piqûre", "urgence"] # ajout manuel de mots
        return sorted(set(mots))


    #print(f"\n ✅ Total de mots liés au médical récupérés : {len(liste_vocab_medical)}")

    #print(f"Liste de mots liés au médical : {liste_vocab_medical}")



# Sujet police

# Sur la page web précédente (lié au médical), nous avons pu utiliser la bibliothèque BeutifulSoup car elle permettait de lire du HTML brut, 
# et donc de récupérer les termes dont nous avions besoin.
# Sur cette nouvelle page web choisie pour récupérer les termes liés à la police, les mots-clés sont ajoutés par JavaScript après le chargement de la page. 
# Il n'a dont pas été possible d'utiliser cette même bibliothèque. 

# La solution a été d'utiliser la bibliothèque Selenium pour simuler un vrai navigateur qiu exécute du JavaScript afin d'afficher les mots-clés.


def get_police_terms():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # pas de fenêtre visible

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("https://www.rimessolides.com/motscles.aspx?m=police") # pour ouvrir la page web

    # Attente pour laisser JS charger les mots
    time.sleep(3)
    # permet d'attendre le temps que les mots clés qui nous intéressent soient chargés par JavaScript

    divs = driver.find_elements(By.CSS_SELECTOR, "div.motcle")
    mots = []
    for div in divs:
        text = div.text.strip().lower()
        if text and text not in mots:
            mots.append(text)
    mots += ["flashball", "lacrymogène", "garde-à-vue"] # ajout manuel de mots
    driver.quit()
    return sorted(set(mots))

#print(f"✅ Total de mots liés à la police récupérés: {len(mots)}")
#print(mots)



# Vocabulaire douche

liste_vocab_douche = ["douche", "laver", "nettoyer"]
print(f"\n ✅ Total de mots liés aux douches publiques récupérés : {len(liste_vocab_douche)}")
print(f"Liste de mots liés aux douches publiques : {liste_vocab_douche}")

# Vocabulaire maraude

liste_vocab_maraude = ["distribution", "nourriture", "manger", "aliment", "association"]
print(f"\n ✅ Total de mots aux maraudes récupérés : {len(liste_vocab_maraude)}")
print(f"Liste de mots liés aux maraudes : {liste_vocab_maraude}")


# On utilise la lemmatisation pour anticiper les analyses NLP qui seront faites dans le script de l'API chatbot

nlp = spacy.load("fr_core_news_sm")

os.makedirs("api_chatbot", exist_ok=True)
output_path = "api_chatbot/vocabulaires.py"

def lemmatize(word_list):
    lemmes = []
    for word in word_list:
        doc = nlp(word)
        for token in doc:
            if token.is_stop or token.is_punct :
                continue # ignore et passe au mot suivant
            lemmes.append(token.lemma_.lower())
    return sorted(set(lemmes))


if __name__ == "__main__":
    medical = get_medical_terms()
    police = get_police_terms()

    lemmes_medical = lemmatize(medical)
    lemmes_police = lemmatize(police)
    lemmes_douche = lemmatize(liste_vocab_douche)
    lemmes_maraude = lemmatize(liste_vocab_maraude)

    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Fichier auto-généré : uniquement les lemmes des vocabulaires\n\n")

        f.write("lemmes_vocab_medical = [\n")
        for mot in lemmes_medical:
            f.write(f'    "{mot}",\n')
        f.write("]\n\n")

        f.write("lemmes_vocab_police = [\n")
        for mot in lemmes_police:
            f.write(f'    "{mot}",\n')
        f.write("]\n\n")

        f.write(f"lemmes_vocab_douche = {lemmes_douche}\n\n")
        f.write(f"lemmes_vocab_maraude = {lemmes_maraude}\n")

    print(f"✅ Fichier généré : {output_path}")