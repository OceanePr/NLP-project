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
import uuid
import csv
from datetime import datetime
import os
import json


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
def make_sentence_for_distribution(distrib): 
    jour = distrib.get("Jour", "jour non précisé")
    adresse = distrib.get("Adresse", "adresse inconnue")
    horaires = distrib.get("Horaires", "horaires inconnus")
    organisation = distrib.get("Organisation", "organisation inconnue")
    sentence = f"- - Le {jour} à l'adresse : {adresse}, aux horaires suivants : {horaires}, au nom de : {organisation}"
    return sentence 

def make_sentence_for_hospital(hospital):
    nom = hospital.get("raison_sociale", "Nom inconnu")
    adresse = hospital.get("adresse_complete", "Adresse inconnue")
    tel = hospital.get("num_tel", "Téléphone non renseigné")
    categorie = hospital.get("categorie_de_l_etablissement", "Catégorie inconnue")
    sentence = f"- {nom}, situé au {adresse}, catégorie : {categorie}, téléphone : {tel}"
    return sentence

def make_sentence_for_shower(doc):
    adresse = doc.get("Adresse", "Adresse inconnue")
    horaires = doc.get("Horaires", "Horaires non précisés")
    mixte = doc.get("Mixite", "Mixité non précisée")
    jour = doc.get("Jour", "Jour non précisé")
    sentence = f"- Adresse : {adresse}, jour : {jour}  horaires : {horaires}, mixité : {mixte}"
    return sentence

def make_sentence_for_police_station(pol):
    adresse = pol.get("Adresse", "Adresse inconnue")
    organisation = pol.get("Organisation", "Etablissement inconnu")
    jour = pol.get("Jour", "Jour non précisé")
    horaires = pol.get("Horaires", "Horaires non précisés")
    sentence = f"- Orgnisation : {organisation}, adresse : {adresse}, jour : {jour}, horaires : {horaires}"
    return sentence



# Chargement du modèle français de spaCy

nlp = spacy.load("fr_core_news_sm")  

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

    awaiting_file = "data/awaiting_days.json"
    days_keywords = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

    if os.path.exists(awaiting_file):
        with open(awaiting_file, "r", encoding="utf-8") as f:
            awaiting_info = json.load(f)

        if awaiting_info.get("waiting"):
            user_days = [day.capitalize() for day in days_keywords if day in chat.message.lower()]
            if user_days:
                csv_path = "data/utilisateur_maraude_feedback.csv"
                df = pd.read_csv(csv_path)
                idx = df[df["uuid"] == awaiting_info["uuid"]].index
                if not idx.empty:
                    df.loc[idx[0], "user_days"] = ", ".join(user_days)
                    df.to_csv(csv_path, index=False)
                os.remove(awaiting_file)
                return ChatResponse(response=f"Merci, nous avons bien noté que vous vous rendez aux maraudes les jours suivants : {', '.join(user_days)}")

    user_msg = chat.message
    spacy_doc = nlp(user_msg)
    print(spacy_doc)



    ################ User context ##########################

    session_file = "data/user_sessions.json"
    user_id_file = "data/current_user.json"

    
    if not os.path.exists(user_id_file):
        return ChatResponse(response="Bonjour ! Bienvenue sur le chatbot pour Infrastructures qui permet de lutter contre la précarité." \
        "Pour commencer, pourriez-vous saisir un identifiant, s'il vous plaît ? (ex: votre prénom).")
    
    # keyword to close the session : "fin"
    if chat.message.strip().lower() == "fin":
        if os.path.exists(user_id_file):
            with open(user_id_file, "r", encoding="utf-8") as f:
                user_id = f.read().strip()
            # delete user data
            if os.path.exists(session_file):
                with open(session_file, "r", encoding="utf-8") as f:
                    session_data = json.load(f)
                session_data.pop(user_id, None)
                with open(session_file, "w", encoding="utf-8") as f:
                    json.dump(session_data, f, ensure_ascii=False)
            os.remove(user_id_file)
        return ChatResponse(response="Votre session est terminée. À bientôt !")


    
    if os.path.exists(session_file):
        with open(session_file, "r", encoding="utf-8") as f:
            session_data = json.load(f)
    else:
        session_data = {}

    detected_theme = "inconnu"
    for token in spacy_doc : 
        lemma = token.lemma_.lower()
        if lemma in lemmes_vocab_maraude:
            detected_theme = "maraude"
            break
        elif lemma in lemmes_vocab_douche:
            detected_theme = "douche"
            break
        elif lemma in lemmes_vocab_medical:
            detected_theme = "médical"
            break
        elif lemma in lemmes_vocab_police:
            detected_theme = "police"
            break
      

    if detected_theme == "inconnu" and "last_theme" in session_data:
        detected_theme = session_data["last_theme"]

    session_data["last_theme"] = detected_theme
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False)

    ############# End of user context #################################



    # Intent classification
    api_method = classify_intent(user_msg)
    print(api_method)
        
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

    response_message = "Je n'ai pas compris votre demande. Pouvez-vous reformuler ?"    
    if not detected_borough and api_method == "GET": 
        response_message = "Je n'ai pas réussi à trouver dans quel arrondissement de Paris vous souhaitez effectuer votre recherche, pourriez-vous me le préciser s'il vous plaît ? "
        
    else : 
 ########### Subject = "maraude" // requête GET ###################
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
                        response_message += "\nAfin d'aider les associations à organiser leurs stocks, pourriez-vous nous dire s'il y a un ou plusieurs jours de la semaine où vous vous rendez généralement aux maraudes dans cet arrondissement ?"

                        feedback_file = "data/utilisateur_maraude_feedback.csv"
                        feedback_entry = {
                            "uuid": str(uuid.uuid4()),
                            "datetime": datetime.now().isoformat(),
                            "borough": detected_borough,
                            "theme": detected_theme,
                            "message": user_msg
                        }

                        file_exists = os.path.isfile(feedback_file)
                        with open(feedback_file, mode="a", newline="", encoding="utf-8") as f:
                            writer = csv.DictWriter(f, fieldnames=feedback_entry.keys())
                            if not file_exists:
                                writer.writeheader()
                            writer.writerow(feedback_entry)
                        
                        with open("data/awaiting_days.json", "w", encoding="utf-8") as f:
                            json.dump({"waiting": True, "uuid": feedback_entry["uuid"]}, f, ensure_ascii=False)


                except Exception as e:
                    response_message = f"Une erreur inattendue est survenue: {e}"
                    print(f"Erreur inattendue: {e}")


 ########### Subject = "maraude" // requête POST ################### Gros doute sur l'utilité ici vu qu'on a un formulaire dédié. Il faudrait que le chatbot donne directement
 # l'url http://127.0.0.1:5000/add_distribution pour que l'utilisateur soit renvoyé vers le formulaire

    #          if api_method == "POST" :
     #           api_url = f"{FLASK_API_BASE_URL}/add_distribution"

                # sans le formulaire, on devrait mettre un payload contenant les données récupérées via NLP.

      #          try:
       #             async with httpx.AsyncClient() as client:
        #                flask_response = await client.post(api_url, data = payload)
         #               flask_response.raise_for_status()
                        
          #              distributions_data = flask_response # la réponse attendue est un formulaire html donc pas de json
           #             message = "La distribution a bien été ajoutée dans la base de données"
            #            response_message = message
             #   except Exception as e:
              #      response_message = f"Une erreur inattendue est survenue lors de l'ajout : {e}"
               #     print(f"Erreur inattendue: {e}")


######### Subject = "Police station" // requête GET ############

        elif detected_theme == "police": 
            api_url = f"{FLASK_API_BASE_URL}/police_stations/borough/{detected_borough}"
        
            try:
                async with httpx.AsyncClient() as client:
                    flask_response = await client.get(api_url)
                    flask_response.raise_for_status() # Lève une exception pour les codes d'erreur HTTP (4xx ou 5xx)
                    
                    police_station_data = flask_response.json()
                    print(police_station_data)
                    sentences = [make_sentence_for_police_station(police) for police in police_station_data]
                    final_sentence = "\n".join(sentences)
                    message = f"Voici les établissements judiciaires dans l'arrondissement n°{detected_borough}: \n" + final_sentence
                    response_message = message
            except Exception as e:
                response_message = f"Une erreur inattendue est survenue: {e}"
                print(f"Erreur inattendue: {e}")
        
          
        
######### Subject = "Douche" // requête GET ############

        elif detected_theme == "douche":
            # To retrieve available bourouh numbers in our public_shower collection
            try:
                async with httpx.AsyncClient() as client:
                    boroughs_response = await client.get(f"{FLASK_API_BASE_URL}/public_showers/available_boroughs")
                    boroughs_response.raise_for_status()
                    douche_arrondissements_disponibles = boroughs_response.json()
            except Exception as e:
                return ChatResponse(response=f"Erreur lors de la récupération des arrondissements disponibles : {e}")

            if detected_borough not in douche_arrondissements_disponibles:
                arr_str = ', '.join([f"{a}e" for a in douche_arrondissements_disponibles])
                response_message = (
                    f"Nous sommes désolées, il n'y a pas de douche publique enregistrée dans l'arrondissement n°{detected_borough}. "
                    f"Voici les arrondissements actuellement couverts : {arr_str}. "
                    "Veuillez indiquer un autre arrondissement parmi cette liste."
                )
                return ChatResponse(response=response_message)

            # To retrive public shower informations
            api_url = f"{FLASK_API_BASE_URL}/public_showers/borough/{detected_borough}"
            try:
                async with httpx.AsyncClient() as client:
                    flask_response = await client.get(api_url)
                    flask_response.raise_for_status()

                    public_shower_data = flask_response.json()
                    print(public_shower_data)

                    sentences = [make_sentence_for_shower(shower) for shower in public_shower_data]
                    final_sentence = "\n".join(sentences)

                    response_message = f"Voici les douches publiques dans l'arrondissement n°{detected_borough}:\n{final_sentence}"
            except Exception as e:
                response_message = f"Une erreur inattendue est survenue: {e}"
                print(f"Erreur inattendue: {e}")

        
          
        
######### Subject = "Hôpitaux" // requête GET ############

        elif detected_theme == "médical": 
            api_url = f"{FLASK_API_BASE_URL}/hospitals/borough/{detected_borough}"
        
            try:
                async with httpx.AsyncClient() as client:
                    flask_response = await client.get(api_url)
                    flask_response.raise_for_status() # Lève une exception pour les codes d'erreur HTTP (4xx ou 5xx)
                    
                    hospital_data = flask_response.json()
                    print(hospital_data)
                    sentences = [make_sentence_for_hospital(hospital) for hospital in hospital_data]
                    final_sentence = "\n".join(sentences)
                    message = f"Voici les hôpitaux dans l'arrondissement n°{detected_borough}: \n" + final_sentence
                    response_message = message
            except Exception as e:
                response_message = f"Une erreur inattendue est survenue: {e}"
                print(f"Erreur inattendue: {e}")
        
          
        else :
            print("Le sujet n'a pas été reconnu parmi police, douche, maraude et hôpital")
            response_message = "Nous n'avons pas reconnu l'un des quatre sujets que nous couvrons : les douches publiques, les hôpitaux, les commissariats et les maraudes"

   

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

