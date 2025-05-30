import pandas as pd
import spacy
import re 
from api.vocabulaires import (
    lemmes_vocab_medical,
    lemmes_vocab_police,
    lemmes_vocab_douche,
    lemmes_vocab_maraude,
)
from fastapi import FastAPI
from spacy.pipeline import EntityRuler
from pydantic import BaseModel
import httpx  # async HTTP client : on l'utilise à la place de request pour sa propriété asynchrone (= possibilité de gérer plusieurs requêtes en même temps)
import asyncio
import requests
from bs4 import BeautifulSoup


# URL de votre API Flask
FLASK_API_BASE_URL = "http://127.0.0.1:5000" # Assurez-vous que c'est le bon port et l'adresse

def classify_intent(message: str):
    message = message.lower()

    if re.search(r"\b(supprimer|annuler|retirer)\b", message):
        return "DELETE"
    elif re.search(r"\b(ajouter|enregistrer|créer)\b", message):
        return "POST"
    elif re.search(r"\b(modifier|changer|mettre à jour)\b", message):
        return "PUT"
    elif re.search(r"\b(y a-t-il|où|quand|est-ce qu'il y a|je cherche|existe|besoin)\b", message):
        return "GET"
    else:
        return "unknown", None

# Function to make a sentence from a dict corresponding to a document in the distribution collection
def make_sentence_for_distribution(dct_distrib): 
    sentence = f"- Le {dct_distrib["Jour"]} à l'adresse : {dct_distrib["Adresse"]}, {dct_distrib["Code Postal"]}, aux horaires suivants : {dct_distrib["Horaires"]}, au nom de : {dct_distrib["Organisation"]} "
    return sentence 
# Chargement du modèle français de spaCy

nlp = spacy.load("fr_core_news_sm")  

# Etant dans un notebook Jupyter, je ne peux pas utiliser un input() pour le moment. Il faudra attendre de transférer le code dans un fichier python .py
# received_text = input(Bonjour ! Que puis-je faire pour vous ?")

#received_text = "Je cherche les horaires d’une maraude dans Paris, si possible près de rue de Robin."
#print ("vous : ", received_text)

app_chatbot = FastAPI(
    title="Chatbot API pour Infrastructures contre la précarité",
    description="Une API de chatbot qui utilise le NLP pour comprendre les requêtes et interroger une API de données.",
    version="1.0.0"
)

# Requête du client
class ChatRequest(BaseModel):
    message: str

# Réponse du bot
class ChatResponse(BaseModel):
    response: str


# Je veux que "Rue de Robin" soit reconnu comme une localisation. Actuellement "Robin" est détecté comme étant une personne.
# On utilise donc le composant de spaCy nommé EntityRuler por spécifier et prioriser des règles d'entités.

ruler = nlp.add_pipe("entity_ruler", before="ner")
 # On crée les patterns à identifier comme étant une localisation. 
 
patterns = [
   
        {
            "label": "LOC",
            "pattern": [
                {"LOWER": {"IN": ["rue", "avenue", "boulevard", "place"]}},
                {"LOWER": {"IN": ["de", "d'", "du", "des"]}},
                {"IS_ALPHA": True, "OP": "+"}  # pour détecter un ou plusieurs mots alphabétiques
            ]
    },
        {
        "label": "LOC",  # Identifier comme une localisation
        "pattern": [{"SHAPE": "ddddd"}]  # Reconnaître les séquences de 5 chiffres
    },
         {
        "label": "BOROUGH", # Pour "13e arrondissement", "1er", "2ème"
        "pattern": [
            {"LOWER": {"REGEX": "\\d+(?:e|er|ème)?"}}, # Ex: "13e", "1er", "2ème"
            {"LOWER": "arrondissement", "OP": "?"} # "arrondissement" est optionnel
        ]
    }
 ]
ruler.add_patterns(patterns)



@app_chatbot.post("/chat", response_model = ChatResponse)
async def user_text(chat: ChatRequest):
    user_msg = chat.message
    spacy_doc = nlp(user_msg)

    print(spacy_doc)
    # Intent classification
    api_method = classify_intent(user_msg)
    print(api_method)

    detected_theme = "inconnu"
    for token in spacy_doc : 
        print(f"{token.text.lower()} → lemma: {token.lemma_.lower()}, POS: {token.pos_}")

        lemma = token.lemma_.lower()
        print(lemma)
        if lemma in lemmes_vocab_maraude:
            detected_theme = "maraude" #{"theme": "médical"}
            break
        elif lemma in lemmes_vocab_douche:
            detected_theme = "douche"#{"theme": "police"}
            break
        elif lemma in lemmes_vocab_medical:
            detected_theme = "médical"#{"theme": "douche"}
            break
        elif lemma in lemmes_vocab_police:
            detected_theme = "police"#{"theme": "maraude"}
            break
        else:
            detected_theme = "inconnu"#{"theme": "inconnu"}

      
    print(f"Thème détecté: {detected_theme}")




    lieux = []
    detected_borough = None
    for ent in spacy_doc.ents:
        if ent.label_ in ["GPE", "LOC", "FAC", "BOROUGH"]:
            lieux.append(ent.text)
            
        # Tentative d'extraction de l'arrondissement
        if ent.label_ == "BOROUGH":
            # Utilise une regex pour extraire le numéro (ex: "13" de "13e arrondissement")
            match = re.search(r"(\d{1,2}(?:e|er|ème)?)", ent.text, re.IGNORECASE)
            print(ent.text)
            if match:
                numbers_as_strings = re.findall(r'\d+', ent.text)

                # Convert the found strings to integers
                detected_borough = [int(num_str) for num_str in numbers_as_strings][0]

    print("LIEUX DÉTECTÉS :", lieux)
    print("ARRONDISSEMENT DÉTECTÉ :", detected_borough)



   # print("LIEUX DÉTECTÉS :", lieux)

   # clean_text = " ".join([
   #    token.lemma_.lower() for token in spacy_doc
   #    if not token.is_stop and not token.is_punct
   # ])
   # print("Texte nettoyé :", clean_text)
    if not detected_borough and api_method == "GET": 
        response_message = "Je n'ai pas réussi à trouver dans quel arrondissement de Paris vous souhaitez effectuer votre recherche, pourriez-vous me le préciser s'il vous plaît ? "
        
    else : 
        if detected_theme == "maraude": 
            if api_method == "GET" :
                api_url = f"{FLASK_API_BASE_URL}/distributions/borough/{detected_borough}"
                try:
                    async with httpx.AsyncClient() as client:
                        flask_response = await client.get(api_url)
                        flask_response.raise_for_status()
                        
                        distributions_data = flask_response.json()
                        # Formater les différentes ditributions toruvées correspondant à la demande initiale
                        sentences = [make_sentence_for_distribution(distrib) for distrib in distributions_data]
                        final_sentence = "\n".join(sentences)
                        message = f"Voici les distributions de repas organisées dans l'arrondissement n°{detected_borough}: \n" + final_sentence
                        response_message = message
                except Exception as e:
                    response_message = f"Une erreur inattendue est survenue: {e}"
                    print(f"Erreur inattendue: {e}")
        if detected_theme == "maraude": 
            ###### Remplacer par le chemin créé pour la route correspondante ############
            api_url = f"{FLASK_API_BASE_URL}/distributions/borough/{detected_borough}"
            #################################################################
            try:
                async with httpx.AsyncClient() as client:
                    flask_response = await client.get(api_url)
                    flask_response.raise_for_status() # Lève une exception pour les codes d'erreur HTTP (4xx ou 5xx)
                    
                    distributions_data = flask_response.json()
                    print(distributions_data)
                    sentences = [make_sentence_for_distribution(distrib) for distrib in distributions_data]
                    final_sentence = "\n".join(sentences)
                    message = f"Voici les douches publiques dans l'arrondissement n°{detected_borough}: \n" + final_sentence
                    response_message = message
            except Exception as e:
                response_message = f"Une erreur inattendue est survenue: {e}"
                print(f"Erreur inattendue: {e}")
            
        else :
            print("test")
            response_message = "Test"

    if detected_theme == "maraude": 
        # --- EXTRACTION DES JOURS ---
        days_keywords = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        detected_days = [day.capitalize() for day in days_keywords if day in user_msg.lower()]

        # Case 1 : missing day and borough
        if not detected_borough and not detected_days:
            response_message = "Pouvez-vous préciser l'arrondissement ainsi que le ou les jours qui vous intéressent pour la maraude ?"


        if not detected_borough:
            response_message = "Dans quel arrondissement cherchez-vous une maraude ?"
        api_url = f"{FLASK_API_BASE_URL}/distributions/borough/{detected_borough}"
        try:
            async with httpx.AsyncClient() as client:
                flask_response = await client.get(api_url)
                flask_response.raise_for_status() # Lève une exception pour les codes d'erreur HTTP (4xx ou 5xx)
                
                distributions_data = flask_response.json()
                response_message = str(distributions_data)
        except Exception as e:
            response_message = f"Une erreur inattendue est survenue: {e}"
            print(f"Erreur inattendue: {e}")     
    else :
        print("test")
        response_message = "Test"

    return ChatResponse(response=response_message)



#  # En attendant d'avoir réalisé l'algorithme de machine learning permettant de classer le texte de l'utilisateur comme étant "santé", 
#  # "judiciaire", "maraude" ou "douche", on simule un sujet = "santé" pour la suite du text.
#  sujet = "santé"
#  # sujet = classifier_subject_model.predict(text)


#  if len(lieux) == 1:
#     print(f"Vous vous intéressé au sujet {sujet} sur la localisation {lieux[0]}")
#  elif len(lieux) == 2:
#     print(f"Vous vous intéressé au sujet {sujet} sur la localisation {lieux[0]}, {lieux[1]}")
#  elif len(lieux) == 3:
#     print(f"Vous vous intéressé au sujet {sujet} sur la localisation {lieux[0]}, {lieux[1]}, {lieux[2]}")
#  elif len(lieux) == 4:
#     print(f"Vous vous intéressé au sujet {sujet} sur la localisation {lieux[0]}, {lieux[1]}, {lieux[2]}, {lieux[3]}")
#  else :
#     print(f"Vous vous intéressé au sujet {sujet}. Pouvez-vous nous donner le code postal, s'il vous plait ?")


#  return classifier(text)


# # Lancer avec : uvicorn script:app --reload

