from flask import Flask, jsonify, request
import mysql.connector
from dotenv import load_dotenv
import os
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app)

# MySQL Configuration
db = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE")
)
cursor = db.cursor()

@app.route("/members")
def members():
    return{"members": ["Member1", "Member2", "Member3"]}

@app.route("/CustomerPage", methods=["GET"])
def get_customers():
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)
    search_query = request.args.get("search", "", type=str)
    offset = (page - 1) * limit

    cursor = db.cursor(dictionary=True)

    if search_query.isdigit():  # If searching by customer ID
        cursor.execute("""
            SELECT customer_id, first_name, last_name, email
            FROM customer 
            WHERE customer_id = %s 
            LIMIT %s OFFSET %s;
        """, (search_query, limit, offset))
    else:  # If searching by first or last name
        cursor.execute("""
            SELECT customer_id, first_name, last_name, email
            FROM customer 
            WHERE first_name LIKE %s OR last_name LIKE %s
            LIMIT %s OFFSET %s;
        """, (f"%{search_query}%", f"%{search_query}%", limit, offset))

    customers = cursor.fetchall()

    # Get total count for pagination
    cursor.execute("SELECT COUNT(*) AS total FROM customer WHERE first_name LIKE %s OR last_name LIKE %s;", 
                   (f"%{search_query}%", f"%{search_query}%"))
    total_customers = cursor.fetchone()["total"]

    cursor.close()

    return jsonify({
        "customers": customers,
        "total": total_customers,
        "page": page,
        "limit": limit
    })
    

@app.route("/add-customer", methods=["POST"])
def add_customer():
    print('si?')
    data = request.json
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")

    if not first_name or not last_name:
        return jsonify({"error": "First and lasr name are required"}), 400

    try:
        store_id = 1
        address_id = 180
        #active = 1
        cursor.execute(
            "INSERT INTO customer (store_id, first_name, last_name, email, address_id) VALUES (%s, %s, %s, %s, %s)",
            (store_id, first_name, last_name, email, address_id)
        )
        db.commit()

        return jsonify({"message": "Customer added successfully"}), 201
    
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

@app.route("/delete-customer", methods=["POST"])
def delete_customer():
    try:
        data = request.json
        cus_id = data.get("customer_id")

        if not cus_id:
            return jsonify({"error": "Customer ID is required"}), 400

        cursor = db.cursor()
        cursor.execute("DELETE FROM customer WHERE customer_id = %s", (cus_id,))
        db.commit()
        cursor.close()

        return jsonify({"message": "Customer deleted successfully"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    
@app.route("/update-customer", methods=["POST"])
def update_customer():
    try:
        data = request.json
        customer_id = data.get("customer_id")
        first_name = data.get("first_name", None)
        last_name = data.get("last_name", None)
        email = data.get("email", None)

        if not customer_id:
            return jsonify({"error": "Customer ID is required"}), 400

        update_fields = []
        params = []

        if first_name:
            update_fields.append("first_name = %s")
            params.append(first_name)
        if last_name:
            update_fields.append("last_name = %s")
            params.append(last_name)
        if email:
            update_fields.append("email = %s")
            params.append(email)

        if not update_fields:
            return jsonify({"error": "No fields provided for update"}), 400

        params.append(customer_id)
        cursor = db.cursor()
        cursor.execute(f"UPDATE customer SET {', '.join(update_fields)} WHERE customer_id = %s", tuple(params))
        db.commit()
        cursor.close()

        return jsonify({"message": "Customer updated successfully"}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/test-db")
def test_db():
    try:
        cursor.execute("SELECT DATABASE()")
        db_name = cursor.fetchone()
        return jsonify({"message": "Database connected!", "database": db_name[0]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
'''
@app.route("/test-actor")
def test_actor():
    try:
        cursor.execute("SELECT actor_id, first_name, last_name FROM actor LIMIT 1")
        actor = cursor.fetchone()  # Get the first row
        
        if actor:
            return jsonify({
                "actor_id": actor[0],
                "first_name": actor[1],
                "last_name": actor[2]
            })
        else:
            return jsonify({"message": "No data found in actor table"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
'''

if __name__ == "__main__":
    app.run(debug=True)