from flask import Flask, jsonify, request
import mysql.connector
from mysql.connector import Error
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


def get_db_connection():
    """Function to get a new database connection."""
    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE")
        )
        return connection
    except Error as e:
        print(f"Error: {e}")
        return None
    
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

@app.route("/customer-rental-history/<int:customer_id>", methods=["GET"])
def get_customer_rental_history(customer_id):
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            r.rental_id,
            f.title, 
            r.rental_date, 
            r.return_date,
            CASE 
                WHEN r.return_date IS NULL THEN 'No' 
                ELSE 'Yes' 
            END AS returned
        FROM rental r
        JOIN inventory i ON r.inventory_id = i.inventory_id
        JOIN film f ON i.film_id = f.film_id
        WHERE r.customer_id = %s
        ORDER BY r.rental_date DESC;
    """, (customer_id,))

    rental_history = cursor.fetchall()
    cursor.close()

    return jsonify({"rental_history": rental_history})

@app.route("/test-db")
def test_db():
    try:
        cursor.execute("SELECT DATABASE()")
        db_name = cursor.fetchone()
        return jsonify({"message": "Database connected!", "database": db_name[0]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/search-films", methods=["GET"])
def get_films():
    search_query = request.args.get("search", "", type=str)
    page = request.args.get("page", 1, type=int)  # Default to page 1
    limit = request.args.get("limit", 10, type=int)  # Default 10 films per page
    offset = (page - 1) * limit  # Calculate offset for pagination

    cursor = db.cursor(dictionary=True)

    if search_query:
        query = """
        SELECT f.film_id, f.title, f.description, f.release_year, f.rating, c.name AS category,
               (SELECT COUNT(i.inventory_id) 
                FROM inventory i
                LEFT JOIN rental r ON i.inventory_id = r.inventory_id AND r.return_date IS NULL
                WHERE i.film_id = f.film_id AND i.store_id = 1 AND r.inventory_id IS NULL) AS available_copies
        FROM film f
        JOIN film_category fc ON f.film_id = fc.film_id
        JOIN film_actor fa ON f.film_id = fa.film_id
        JOIN actor a ON fa.actor_id = a.actor_id
        JOIN category c ON fc.category_id = c.category_id
        WHERE f.title LIKE %s
        OR c.name LIKE %s
        OR CONCAT(a.first_name, ' ', a.last_name) LIKE %s
        LIMIT %s OFFSET %s
        """
        wildcard_search = f"%{search_query}%"
        cursor.execute(query, (wildcard_search, wildcard_search, wildcard_search, limit, offset))
    else:
        query = """
        SELECT f.film_id, f.title, f.description, f.release_year, f.rating, c.name AS category,
               (SELECT COUNT(i.inventory_id) 
                FROM inventory i
                LEFT JOIN rental r ON i.inventory_id = r.inventory_id AND r.return_date IS NULL
                WHERE i.film_id = f.film_id AND i.store_id = 1 AND r.inventory_id IS NULL) AS available_copies
        FROM film f
        LEFT JOIN film_category fc ON f.film_id = fc.film_id
        LEFT JOIN category c ON fc.category_id = c.category_id
        LIMIT %s OFFSET %s
        """
        
        cursor.execute(query, (limit, offset))

    films = cursor.fetchall()

    # Get total count of films (for pagination)
    count_query = "SELECT COUNT(*) AS total FROM film"
    cursor.execute(count_query)
    total_films = cursor.fetchone()["total"]

    cursor.close()

    return jsonify({"films": films, "total": total_films, "page": page, "limit": limit})

@app.route("/available-films", methods=["GET"])
def get_available_films():
    cursor = db.cursor(dictionary=True)

    query = """
    SELECT f.film_id, f.title, f.description, f.release_year, f.rating, c.name AS category, COUNT(i.inventory_id) AS available_copies
    FROM film f
    JOIN film_category fc ON f.film_id = fc.film_id
    JOIN category c ON fc.category_id = c.category_id
    JOIN inventory i ON f.film_id = i.film_id
    LEFT JOIN rental r ON i.inventory_id = r.inventory_id AND r.return_date IS NULL
    WHERE i.store_id = 1 AND r.inventory_id IS NULL
    GROUP BY f.film_id, f.title, f.description, f.release_year, f.rating, c.name;
    """
    
    cursor.execute(query)
    films = cursor.fetchall()
    cursor.close()
    
    return jsonify(films)


@app.route("/rent-film", methods=["POST"])
def rent_film():
    data = request.json
    film_id = data.get("film_id")
    customer_id = data.get("customer_id")
    staff_id = 1  # Assuming Store 1's staff handles rentals

    cursor = db.cursor(dictionary=True)

    # Find an available inventory_id for this film
    find_inventory_query = """
    SELECT i.inventory_id 
    FROM inventory i
    LEFT JOIN rental r ON i.inventory_id = r.inventory_id AND r.return_date IS NULL
    WHERE i.film_id = %s AND i.store_id = 1 AND r.inventory_id IS NULL
    LIMIT 1;
    """
    cursor.execute(find_inventory_query, (film_id,))
    available_inventory = cursor.fetchone()

    if not available_inventory:
        return jsonify({"success": False, "message": "No available copies"}), 400

    inventory_id = available_inventory["inventory_id"]

    # Insert into rental table
    rent_query = """
    INSERT INTO rental (rental_date, inventory_id, customer_id, staff_id, last_update)
    VALUES (NOW(), %s, %s, %s, NOW());
    """
    cursor.execute(rent_query, (inventory_id, customer_id, staff_id))
    db.commit()
    cursor.close()

    return jsonify({"success": True, "message": "Rental successful!"})


@app.route("/top-actors", methods=["GET"])
def get_top_actors():
    # Get a new database connection
    connection = get_db_connection()
    if connection is None:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    # Query to fetch the top actors based on rental count
    query = """
        SELECT a.actor_id, a.first_name, a.last_name, COUNT(*) AS movies
        FROM film f
        JOIN film_actor b ON f.film_id = b.film_id
        JOIN actor a ON b.actor_id = a.actor_id
        GROUP BY a.actor_id
        ORDER BY movies DESC
        LIMIT 5;
    """

    cursor.execute(query)
    actors = cursor.fetchall()

    # Now, for each actor, fetch their top 5 rented films
    for actor in actors:
        actor_id = actor['actor_id']

        # Query to fetch the top 5 rented films for the current actor
        film_query = """
        SELECT f.film_id, f.title, COUNT(*) AS rental_count
        FROM rental r
        JOIN inventory i ON r.inventory_id = i.inventory_id
        JOIN film f ON i.film_id = f.film_id
        JOIN film_actor fa ON f.film_id = fa.film_id
        WHERE fa.actor_id = %s
        GROUP BY f.film_id, f.title
        ORDER BY rental_count DESC
        LIMIT 5;
        """

        cursor.execute(film_query, (actor_id,))
        top_films = cursor.fetchall()

        # Add the top films to each actor
        actor['top_films'] = top_films

    cursor.close()
    connection.close()  # Close the connection after use
    return jsonify(actors)

@app.route("/top-movies", methods=["GET"])
def get_top_movies():
    # Get a new database connection
    connection = get_db_connection()
    if connection is None:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    # Query to get the top 5 most rented movies
    query = """
        SELECT f.film_id, f.title, f.description, f.release_year, f.rating, COUNT(*) AS rented_count
        FROM rental r
        JOIN inventory i ON r.inventory_id = i.inventory_id
        JOIN film f ON i.film_id = f.film_id
        GROUP BY f.film_id, f.title, f.description, f.release_year, f.rating
        ORDER BY rented_count DESC
        LIMIT 5;
    """

    cursor.execute(query)
    top_movies = cursor.fetchall()

    cursor.close()
    connection.close()  # Close the connection after use
    return jsonify(top_movies)



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