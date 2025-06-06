from pymongo import MongoClient
from flask_pymongo import PyMongo
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template 
from flask import Flask, request, jsonify
from bson.json_util import dumps
from flask_pymongo import PyMongo
import os


app = Flask(__name__)

# Just an example using sql alchemy, but i will try to use mongoDB instead
# app.config['MONGO_URI'] = 'mongodb://localhost:27017/infrastructures_precarite' (en local)
app.config['MONGO_URI'] = os.environ.get("MONGO_URI") # avec déploiement
db = PyMongo(app)


@app.route('/')
def home():
    return '<h1>Welcome to Infrastructures against insecurity API </h1>'


# Route #1 : add a distribution in our MongoDB collection. You will need a borough number.

@app.route('/add_distribution', methods=['GET', "POST"])
def add_distribution():
    if request.method == 'POST':
        # Check if content type is JSON
        if request.is_json:
            data = request.get_json()
        else:
            # Fallback for form data, though not ideal for API calls
            data = request.form

        try:
            cp = data["cp"]
            address = data["address"]
            city = data["city"]
            schedules = data["schedules"]
            day = data["day"]
            organisation = data["organisation"]
            borough = data["borough"]

            new_distrib = {
                "Code Postal": int(cp),
                "Adresse": address,
                "Ville": city,
                "Horaires": schedules,
                "Jour": day,
                "Organisation": organisation,
                "arrondissement": int(borough),
            }


            print(f"Adding to DB: {new_distrib}")
            db.db.meal_distribution.insert_one(new_distrib)

            return jsonify({"message": "Distribution added successfully!", "data": new_distrib}), 201
        except KeyError as e:
            return jsonify({"error": f"Missing data: {e}"}), 400
        except ValueError as e:
            return jsonify({"error": f"Invalid data type for field: {e}"}), 400
    return render_template('add_distrib.html')

# Route #2 : get informations about a distribution through our MongoDB collection. You will need a borough number.

@app.route('/distributions/borough/<string:borough_nb>', methods=['GET'])
def get_distributions_by_borough(borough_nb):
    """
    Retrieves all meal distributions for a given borough.
    The borough name is passed as a string in the URL.
    """
    meal_distributions_collection = db.db.meal_distribution # 
    
    # Simple exact match (case-sensitive):
    distributions = list(meal_distributions_collection.find({"arrondissement": int(borough_nb)}))

    if distributions:
        # dumps handles MongoDB's ObjectId for JSON serialization
        return dumps(distributions), 200 # 200 OK
    else:
        # Return a 404 Not Found if no distributions are found for that borough
        return jsonify({"message": f"No meal distributions found for borough: {borough_nb}"}), 404
    
# Route 2-1 : get borough number from meal distribution
@app.route("/meal_distribution/available_boroughs", methods=["GET"])
def get_meal_distribution_boroughs():
    try:
        boroughs = db.db["meal_distribution"].distinct("arrondissement")
        return jsonify(sorted(boroughs)), 200
    except Exception as e:
        print(f"Erreur Flask - meal distribution boroughs: {e}")
        return jsonify({"error": str(e)}), 500
    
# Route 3 : get informations about police stations through our MongoDB collection. You will need an borough number.

@app.route('/police_stations/borough/<string:borough_nb>', methods=['GET'])
def get_police_stations_info_by_borough(borough_nb):
    """
    Retrieves all police stations informations for a given borough.
    The borough name is passed as a string in the URL.
    """
    police_stations_collection = db.db.police_stations # 
    
    # Simple exact match (case-sensitive):
    police_stations = list(police_stations_collection.find({"arrondissement": int(borough_nb)}))

    if police_stations:
        # dumps handles MongoDB's ObjectId for JSON serialization
        return dumps(police_stations), 200 # 200 OK
    else:
        # Return a 404 Not Found if no distributions are found for that borough
        return jsonify({"message": f"No police station found for borough: {borough_nb}"}), 404


# Route 4 : get informations about public showers through our MongoDB collection. You will need an borough number.

@app.route('/public_showers/borough/<string:borough_nb>', methods=['GET'])
def get_public_showers_info_by_borough(borough_nb):
    """
    Retrieves all public showers informations for a given borough.
    The borough name is passed as a string in the URL.
    """
    public_showers_collection = db.db.public_showers # 
    
    # Simple exact match (case-sensitive):
    public_showers = list(public_showers_collection.find({"arrondissement": int(borough_nb)}))

    if public_showers:
        # dumps handles MongoDB's ObjectId for JSON serialization
        return dumps(public_showers), 200 # 200 OK
    else:
        # Return a 404 Not Found if no distributions are found for that borough
        return jsonify({"message": f"No public shower found for borough: {borough_nb}"}), 404


# Route 4-1 : get borough number from public showers
@app.route("/public_showers/available_boroughs", methods=["GET"])
def get_public_shower_boroughs():
    try:
        boroughs = db.db["public_showers"].distinct("arrondissement")
        return jsonify(sorted(boroughs)), 200
    except Exception as e:
        print(f"Erreur Flask - public showers boroughs: {e}")
        return jsonify({"error": str(e)}), 500



# Route 5 : get informations about public hospitals our MongoDB collection. You will need an borough number.

@app.route('/hospitals/borough/<string:borough_nb>', methods=['GET'])
def get_hospitals_info_by_borough(borough_nb):
    """
    Retrieves all hospital informations for a given borough.
    The borough name is passed as a string in the URL.
    """
    hospitals_collection = db.db.hospitals # 
    
    # Simple exact match (case-sensitive):
    hospitals = list(hospitals_collection.find({"arrondissement": int(borough_nb)}))

    if hospitals:
        # dumps handles MongoDB's ObjectId for JSON serialization
        return dumps(hospitals), 200 # 200 OK
    else:
        # Return a 404 Not Found if no distributions are found for that borough
        return jsonify({"message": f"No hospital found for borough: {borough_nb}"}), 404



# To check all available routes : go to your borwser and put "http://127.0.0.1:5000/routes"

@app.route("/routes", methods=["GET"])
def list_routes():
    import urllib
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        line = urllib.parse.unquote(f"{rule.endpoint}: {rule.rule} [{methods}]")
        output.append(line)
    return "<br>".join(output)


if __name__ == '__main__':
    app.run(debug=True) # debug=True for development, not production
