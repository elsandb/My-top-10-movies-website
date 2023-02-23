import os
from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import fields, validators
import requests
import sqlalchemy as sa

TMDB_API_KEY = os.getenv('API_KEY')
TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"

# Make flask-app
app = Flask(__name__)

# Connect app to bootstrap
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
Bootstrap(app)

# Make database: Connect app to SQLAlchemy / SQLite
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///movies.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Make class for the Movie-table
class Movie(db.Model):
    """Movie-table. Columns: 'id' (id is th primary_key), 'title', 'year', 'description',
    'rating', 'ranking', 'review', 'img_url'."""
    id = db.Column(db.Integer, primary_key=True)
    title = sa.schema.Column(sa.types.String(300), unique=True, nullable=False)
    year = sa.schema.Column(sa.types.Integer, nullable=False)
    description = sa.schema.Column(sa.types.String(1000), unique=True, nullable=False)
    rating = sa.schema.Column(sa.types.Float)
    ranking = sa.schema.Column(sa.types.Integer, nullable=True)
    review = sa.schema.Column(sa.types.String(200), nullable=True)
    img_url = sa.schema.Column(sa.types.String, nullable=False)


class RateMovieForm(FlaskForm):

    rating = fields.FloatField(label='Your rating out of 10 (e.g. 7.5)', validators=[validators.InputRequired()])
    review = fields.TextAreaField(label='Your review', validators=[validators.InputRequired()])
    done = fields.SubmitField(label='Done')


class AddForm(FlaskForm):
    title_query = fields.StringField(label='Movie title', validators=[validators.InputRequired()])
    add_button = fields.SubmitField(label='Add movie')


@app.route("/")
def home():
    movies = db.session.query(Movie).order_by(Movie.rating.desc())
    for (ranking, movie) in enumerate(movies):
        movie.ranking = ranking + 1
        db.session.commit()
    movies_reversed = reversed([movie for movie in movies])
    return render_template("index.html", all_movies=movies_reversed)


def tmdb_search(query):
    """Uses the query (string) to search for movie titles via an API-call to
    The Movie Databse API (docs: https://developers.themoviedb.org).
    Returns a list of lists: [title, release-year, id] for the search results."""
    params = {
        'api_key': TMDB_API_KEY,
        'Content-Type': "application/json;charset=utf-8",
        'query': query
    }
    response = requests.get(url=TMDB_SEARCH_URL, params=params)
    response.raise_for_status()
    movies_json = response.json()['results']
    title_year_id_list = [
        [
            movie['title'], movie['release_date'].split('-')[0], movie['id']
        ]
        for movie in movies_json
    ]
    return title_year_id_list


def get_movie_details(movie_id):
    params = {'api_key': TMDB_API_KEY}
    details = requests.get(url=f"https://api.themoviedb.org/3/movie/{int(movie_id)}",
                           params=params).json()
    return details


@app.route("/add", methods=["GET", "POST"])
def add():
    add_form = AddForm()
    if add_form.validate_on_submit():
        user_query = add_form.title_query.data
        return redirect(url_for('select', user_query=user_query))
    return render_template("add.html", add_form=add_form)


@app.route("/select", methods=["GET", "POST"])
def select():
    if request.method == 'GET':
        user_query = request.args.get('user_query')
        tmdb_list = tmdb_search(user_query)

        movie_id = request.args.get('movie_id')

        if movie_id is not None:
            details = get_movie_details(movie_id)
            new_movie = Movie(
                title=details['title'],
                year=int(details['release_date'].split('-')[0]),
                description=details['overview'],
                rating=0,
                ranking=0,
                review='',
                img_url=f"{TMDB_IMAGE_URL}{details['poster_path']}"
            )
            with app.app_context():
                db.session.add(new_movie)
                db.session.commit()
                new_movie_id = new_movie.id
            return redirect(url_for('update', movie_id=new_movie_id))
        return render_template('select.html', tmdb_list=tmdb_list)


@app.route("/update", methods=["GET", "POST"])
def update():
    movie_id = request.args.get('movie_id')         # GET REQUEST
    movie_to_update = db.session.get(Movie, movie_id)
    print(f"{movie_to_update = }")

    up_form = RateMovieForm()

    if up_form.validate_on_submit():                # POST REQUEST
        rating = up_form.rating.data
        review = up_form.review.data
        print(f"{rating = }\n{type(rating) = }\n{review = }")

        movie_to_update.rating = rating
        movie_to_update.review = review
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('update.html', update_form=up_form,
                           movie_to_update=movie_to_update)


@app.route("/delete", methods=["GET", "POST"])
def delete():
    movie_id = request.args.get('movie_id')
    movie_to_delete = db.session.get(Movie, movie_id)
    db.session.delete(movie_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
