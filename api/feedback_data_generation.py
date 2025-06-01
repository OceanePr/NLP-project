import csv
import uuid
from datetime import datetime
import random

boroughs = list(range(1, 21))
messages = [
    "Y a-t-il une distribution de repas aujourd'hui ?",
    "Où manger dans le quartier ?",
    "Y a-t-il une maraude prévue cette semaine ?",
    "Je cherche de l'aide pour manger."
]
jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]

with open("data/utilisateur_maraude_feedback.csv", "a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["uuid", "datetime", "borough", "theme", "message", "user_days"])
    for _ in range(2000):  # nombre de lignes à générer
        writer.writerow({
            "uuid": str(uuid.uuid4()),
            "datetime": datetime.now().isoformat(),
            "borough": random.choice(boroughs),
            "theme": "maraude",
            "message": random.choice(messages),
            "user_days": ", ".join(random.sample(jours, k=random.randint(0, 3)))
        })
