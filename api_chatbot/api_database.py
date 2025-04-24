from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_pymongo import PyMongo
from pymongo import Mongoclient


app = Flask(__name__)

# Just an example using sql alchemy, but i will try to use mongoDB instead
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

class Baths_showers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    address = db.Column(db.String(80), unique=True, nullable=False)

    def __repr__(self):
        return f"Shower(name = {self.name}, address = {self.address})"


@app.route('/')
def home():
    return '<h1>Flask REST API</h1>'

if __name__ == '__main__':
    app.run(debug=True) # debug=True for development, not production