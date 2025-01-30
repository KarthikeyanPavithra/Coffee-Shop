import os
from flask import Flask, request, jsonify, abort
from sqlalchemy import exc
import json
from flask_cors import CORS

from .database.models import db_drop_and_create_all, setup_db, Drink
from .auth.auth import AuthError, requires_auth

app = Flask(__name__)
setup_db(app)
CORS(app)

with app.app_context():
    db_drop_and_create_all()

# ROUTES
@app.route('/drinks', methods=['GET'])
def get_drinks():
    try:
        drinks = Drink.query.all()  # Fetch all drinks
        drinks_list = [drink.short() for drink in drinks]  # Use .short() representation
        
        return jsonify({
            "success": True,
            "drinks": drinks_list
        }), 200  # Return response with status 200

    except Exception as e:
        abort(500, description=str(e))  # Return 500 if something goes wrong

@app.route('/drinks-detail', methods=['GET'])
@requires_auth('get:drinks-detail')
def get_drinks_detail(payload):
    try:
        # Query all drinks from the database
        drinks = Drink.query.all()

        # Convert drinks to their long representation
        drinks_detail = [drink.long() for drink in drinks]

        return jsonify({"success": True, "drinks": drinks_detail}), 200
    except Exception as e:
        abort(500, description=str(e))

@app.route('/drinks', methods=['POST'])
@requires_auth('post:drinks')
def create_drink(payload):
    try:
        # Get request data
        body = request.get_json()
        if not body:
            abort(400, description="No data provided")

        # Extract required fields
        title = body.get('title')
        recipe = body.get('recipe')

        if not title or not recipe:
            abort(400, description="Title and recipe are required")

        # Ensure recipe is in correct format
        if not isinstance(recipe, list) or not all(isinstance(item, dict) for item in recipe):
            abort(400, description="Recipe must be a list of objects")

        # Convert recipe list to JSON string before saving
        drink = Drink(title=title, recipe=json.dumps(recipe))
        drink.insert()  # Insert into DB

        # Return response with the new drink's long representation
        return jsonify({
            "success": True,
            "drinks": [drink.long()]
        }), 201  # 201 Created

    except Exception as e:
        abort(500, description=str(e))

@app.route('/drinks/<int:id>', methods=['PATCH'])
@requires_auth('patch:drinks')
def update_drink(payload, id):
    try:
        # Find the drink by ID
        drink = Drink.query.get(id)
        if not drink:
            abort(404, description="Drink not found")

        # Get the request body
        body = request.get_json()
        if not body:
            abort(400, description="No data provided")

        if 'title' in body:
            drink.title = body['title']

        if 'recipe' in body:
            recipe = body['recipe']
            
            if not isinstance(recipe, list) or not all(isinstance(item, dict) for item in recipe):
                abort(400, description="Recipe must be a list of objects")

            drink.recipe = json.dumps(recipe)

        # Save the updated drink
        drink.update()  # Save changes in DB

        # Return updated drink
        return jsonify({
            "success": True,
            "drinks": [drink.long()]
        }), 200

    except Exception as e:
        abort(500, description=str(e))

@app.route('/drinks/<int:id>', methods=['DELETE'])
@requires_auth('delete:drinks')
def delete_drink(payload, id):
    try:
        # Find the drink by ID (automatically raises 404 if not found)
        drink = Drink.query.get(id)
        if not drink:
            abort(404, description="Drink not found")

        # Delete the drink using the model's delete method
        drink.delete()

        # Return success response
        return jsonify({
            "success": True,
            "delete": id
        }), 200

    except Exception as e:
        abort(500, description=str(e))

# Error Handling
@app.errorhandler(422)
def unprocessable(error):
    return jsonify({
        "success": False,
        "error": 422,
        "message": error.description
    }), 422

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": 404,
        "message": error.description
    }), 404

@app.errorhandler(400)
def no_data_found(error):
    return jsonify({
        "success": False,
        "error": 400,
        "message": error.description
    }), 400

# Error handler for AuthError (Custom error handler)
@app.errorhandler(AuthError)
def handle_auth_error(error):
    response = error.get_response()
    response.data = jsonify({
        "success": False,
        "error": error.status_code,
        "message": error.error['description']
    }).data
    response.content_type = "application/json"
    return response

# Global error handler for all other exceptions
@app.errorhandler(500)
def handle_internal_server_error(error):
    return jsonify({
        "success": False,
        "error": 500,
        "message": "Internal Server Error: " + str(error)
    }), 500
