import sqlite3
from flask import Flask, g, jsonify, send_file, request


app = Flask("movie-app")

DATABASE = "movies.db"

@app.get("/")
def hello():
    return jsonify({"message": "Movies API"})

@app.route("/about")
def about():
    print("About page was visited")
    return "<h1>About the Movies API</h1><p>This server will manage movie data.</p>"

@app.route("/movie")
def movie():
    movie_title = "Inception"
    return jsonify({
        "title": movie_title,
        "year": 2010,
        "genre": "Sci-Fi"
    })

@app.get("/movies")
def list_movies():
    db = get_db()
    rows = db.execute("SELECT * FROM movies").fetchall()
    movies = [dict(row) for row in rows]
    return jsonify(movies)

@app.post("/movies")
def create_movie():
    data = request.get_json()

    # Basic validation
    if data is None:
        return jsonify({"error": "Request body must be JSON"}), 400

    title = data.get("title")
    director_id = data.get("director_id")
    year = data.get("year")  # optional

    if not title or director_id is None:
        return jsonify({"error": "Missing required fields: title and director_id"}), 400

    db = get_db()

    try:
        cursor = db.execute(
            "INSERT INTO movies (title, year, director_id) VALUES (?, ?, ?)",
            (title, year, director_id)
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify({
            "error": "Movie with that title and year already exists."
        }), 409
    
    new_id = cursor.lastrowid

    return (
        jsonify({
            "id": new_id,
            "title": title,
            "year": year,
            "director_id": director_id
        }),
        201,
        {"Location": f"/movies/{new_id}"}
    )    


@app.get("/movies/<int:movie_id>")
def get_movie(movie_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM movies WHERE id = ?",
        (movie_id,)
    ).fetchone()

    if row is None:
        return jsonify({"error": "Movie not found"}), 404

    return jsonify(dict(row))

@app.get("/directors/<int:director_id>/movies")
def get_director_with_movies(director_id):
    db = get_db()
    rows = db.execute(
        """
        SELECT
            directors.id AS director_id,
            directors.name AS director_name,
            directors.country AS director_country,
            movies.id AS movie_id,
            movies.title AS movie_title,
            movies.year AS movie_year,
            movies.rating AS movie_rating
        FROM directors
        LEFT JOIN movies ON movies.director_id = directors.id
        WHERE directors.id = ?    
        """,
        (director_id,)
    ).fetchall()

    if not rows:
        return jsonify({"error": "Director not found"}), 404

    first = rows[0]
    result = {
        "id": first["director_id"],
        "name": first["director_name"],
        "country": first["director_country"],
        "movies": []
    }

    for row in rows:
        if row["movie_id"] is None:
            continue
        result["movies"].append({
            "id": row["movie_id"],
            "title": row["movie_title"],
            "year": row["movie_year"],
            "rating": row["movie_rating"],
        }),
    

    return jsonify(result), 200
    

@app.get("/movies/<int:movie_id>/full")
def get_full_movie(movie_id):
    db = get_db()
    row = db.execute(
        """
        SELECT
            movies.id AS movie_id,
            movies.title,
            movies.year,
            movies.rating,
            directors.id AS director_id,
            directors.name AS director_name,
            directors.country AS director_country
        FROM movies
        JOIN directors ON movies.director_id = directors.id
        WHERE movies.id = ?
        """,
        (movie_id,)
    ).fetchone()

    if row is None:
        return jsonify({"error": "Movie not found"}), 404

    movie = {
        "id": row["movie_id"],
        "title": row["title"],
        "year": row["year"],
        "rating": row["rating"],
        "director": {
            "id": row["director_id"],
            "name": row["director_name"],
            "country": row["director_country"],
        },
    }

    return jsonify(movie)

@app.route("/movies/<int:movie_id>", methods=["PATCH"])
def update_movie(movie_id):
    data = request.get_json()

    if data is None:
        return jsonify({"error": "Request body must be JSON"}), 400

    # For now, only allow updating the title
    new_title = data.get("title")

    if not new_title:
        return jsonify({"error": "Nothing to update: 'title' is required for this PATCH"}), 400

    db = get_db()
    cursor = db.execute(
        "UPDATE movies SET title = ? WHERE id = ?",
        (new_title, movie_id)
    )
    db.commit()

    if cursor.rowcount == 0:
        # No movie with that id
        return jsonify({"error": "Movie not found"}), 404

    # Success: return the updated movie (or you could choose 204 with no body)
    row = db.execute(
        "SELECT * FROM movies WHERE id = ?",
        (movie_id,)
    ).fetchone()

    return jsonify(dict(row)), 200

@app.delete("/movies/<int:movie_id>")
def delete_movie(movie_id):
    db = get_db()

    cursor = db.execute(
        "DELETE FROM movies WHERE id = ?",
        (movie_id,)
    )
    db.commit()

    if cursor.rowcount == 0:
        # No movie with that id
        return jsonify({"error": "Movie not found"}), 404

    # Movie was detected successfully
    return "", 204

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

if __name__ == "__main__":
    app.run(debug=True)
