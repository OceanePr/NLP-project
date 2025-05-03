# Chargement du modèle français de spaCy

nlp = spacy.load("fr_core_news_sm")  

# Etant dans un notebook Jupyter, je ne peux pas utiliser un input() pour le moment. Il faudra attendre de transférer le code dans un fichier python .py
# received_text = input(Bonjour ! Que puis-je faire pour vous ?")

received_text = "Je cherche les horaires d’une maraude dans Paris, si possible près de rue de Robin."
print ("vous : ", received_text)

# Je veux que "Rue de Robin" soit reconnu comme une localisation. Actuellement "Robin" est détecté comme étant une personne.
# On utilise donc le composant de spaCy nommé EntityRuler por spécifier et prioriser des règles d'entités.
from fastapi import FastAPI
from spacy.pipeline import EntityRuler

app_chatbot = FastAPI()

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
    }
 ]
ruler.add_patterns(patterns)



@app_chatbot.post("/user/")
def user_text(text: str):
 
 spacy_doc = nlp(received_text)

 for token in spacy_doc : 
    print(f"{token.text.lower()} → lemma: {token.lemma_.lower()}, POS: {token.pos_}")
    
 for ent in spacy_doc.ents:
    print(f"{ent.text} → label: {ent.label_}")

 lieux = [ent.text for ent in spacy_doc.ents if ent.label_ in ["GPE", "LOC", "FAC"]]
 print("LIEUX DÉTECTÉS :", lieux)

 clean_text = " ".join([
    token.lemma_.lower() for token in spacy_doc
    if not token.is_stop and not token.is_punct
])
 print("Texte nettoyé :", clean_text)

 # En attendant d'avoir réalisé l'algorithme de machine learning permettant de classer le texte de l'utilisateur comme étant "santé", 
 # "judiciaire", "maraude" ou "douche", on simule un sujet = "santé" pour la suite du text.
 sujet = "santé"
 # sujet = classifier_subject_model.predict(text)


 if len(lieux) == 1:
    print(f"Vous vous intéressé au sujet {sujet} sur la localisation {lieux[0]}")
 elif len(lieux) == 2:
    print(f"Vous vous intéressé au sujet {sujet} sur la localisation {lieux[0]}, {lieux[1]}")
 elif len(lieux) == 3:
    print(f"Vous vous intéressé au sujet {sujet} sur la localisation {lieux[0]}, {lieux[1]}, {lieux[2]}")
 elif len(lieux) == 4:
    print(f"Vous vous intéressé au sujet {sujet} sur la localisation {lieux[0]}, {lieux[1]}, {lieux[2]}, {lieux[3]}")
 else :
    print(f"Vous vous intéressé au sujet {sujet}. Pouvez-vous nous donner le code postal, s'il vous plait ?")


 return classifier(text)


# Lancer avec : uvicorn script:app --reload

