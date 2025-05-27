from pymongo import MongoClient
from flask_pymongo import PyMongo
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template 
from flask import Flask, request, jsonify
from bson.json_util import dumps 


app = Flask(__name__)

# Just an example using sql alchemy, but i will try to use mongoDB instead
app.config['MONGO_URI'] = 'mongodb://localhost:27017/infrastructures_precarite'
db = PyMongo(app)

# class Baths_showers(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(80), unique=True, nullable=False)
#     address = db.Column(db.String(80), unique=True, nullable=False)

#     def __repr__(self):
#         return f"Shower(name = {self.name}, address = {self.address})"


@app.route('/')
def home():
    return '<h1>Welcome to Infrastructures against insecurity API </h1>'


@app.route('/add_distribution', methods=['GET', "POST"])
def add_distribution():
    if request.method == 'POST':
        cp = request.form["cp"]
        address = request.form["address"] 
        city = request.form["city"]        
        schedules = request.form["schedules"] 
        day = request.form["day"]   
        organisation = request.form["organisation"] 
        borough = request.form["borough"]  

        
       # info to create a new movie title and plot
        new_distrib = {
           "Code Postal": int(cp),
           "Adresse": address, 
           "Ville": city,
           "Horaires": schedules,
           "Jour": day,
           "Organisation": organisation,
           "arrondissement": int(borough), 
       }  
        
        db.db.meal_distribution.insert_one(new_distrib)
        return render_template('add_distrib_success.html', cp=cp, address=address)
    return render_template('add_distrib.html')

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

# @app.route('/get_bath_by_borough', methods=['GET'])
# def get_bath_by_borough(borough_nb):
        
#     bath_collection = db.products # Access your 'products' collection
    
#     # Find all documents in the 'products' collection
#     # .find() returns a cursor, so you need to iterate or convert it
#     all_products = list(products_collection.find()) 
    
#     # MongoDB's ObjectId is not directly JSON serializable.
#     # dumps from bson.json_util handles this gracefully.
#     return dumps(all_products), 200 # 200 OK status code


if __name__ == '__main__':
    app.run(debug=True) # debug=True for development, not production