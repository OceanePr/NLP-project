import csv
import uuid
from datetime import datetime, timedelta
import random

boroughs = list(range(1, 21))
messages = [
    "Y a-t-il une distribution de repas aujourd'hui ?",
    "Où manger dans le quartier ?",
    "Y a-t-il une maraude prévue cette semaine ?",
    "Je cherche de l'aide pour manger."
]
jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]

# Période : entre la date du jour et 4 mois avant
date_fin = datetime.now()
date_debut = date_fin - timedelta(days=120)

# Génération des données
with open("data/utilisateur_maraude_feedback.csv", "a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["uuid", "datetime", "borough", "theme", "message", "user_days"])
    for _ in range(3000):
        random_date = date_debut + timedelta(
            seconds=random.randint(0, int((date_fin - date_debut).total_seconds()))
        )
        writer.writerow({
            "uuid": str(uuid.uuid4()),
            "datetime": random_date.isoformat(),
            "borough": random.choice(boroughs),
            "theme": "maraude",
            "message": random.choice(messages),
            "user_days": ", ".join(random.sample(jours, k=random.randint(0, 3)))
        })
