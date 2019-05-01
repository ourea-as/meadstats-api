import datetime
import json
import logging
import os
from statistics import mean

import pycountry
from flask import Flask, request, jsonify, redirect, make_response
from flask_jwt_extended import (JWTManager, create_access_token, decode_token)
from flask_cors import CORS
from flask_socketio import SocketIO
from requests import HTTPError
from sqlalchemy import func

from .untappd_api import UntappdAPI
from .models import db, ma, User, user_schema, Checkin, checkins_schema, Beer, beer_schema, checkin_schema, Brewery, Venue


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

    # Load config
    if os.getenv('FLASK_ENV') == "development":
        app.config.from_object('app.config.DevelopmentConfig')
    elif os.getenv('FLASK_ENV') == "production":
        app.config.from_object('app.config.ProductionConfig')
    else:
        app.logger.warn(
            "No configuration specified. Falling back to production")
        app.config.from_object('app.config.ProductionConfig')

    db.init_app(app)
    ma.init_app(app)
    socketio = SocketIO(app)
    jwt = JWTManager(app)
    CORS(app)

    untappd_api = UntappdAPI(app.config['UNTAPPD_CLIENT_ID'],
                             app.config['UNTAPPD_CLIENT_SECRET'])

    @app.route('/auth_callback')
    def auth_callback():
        """
        Endpoint called from untappd after successful user authentication
        Contains a code which the server needs to send to the untappd server to obtain access token

        Returns 301 with a JWT token stored in a cookie jwt_token on successful authentication.

        This function also fetches user info if user is new
        """

        # Send token to Untappd servers in order to obtain access token
        code = request.args.get('code')

        try:
            untappd_access_token = untappd_api.authenticate(code, f"{app.config['API_DOMAIN']}/auth_callback")
        except HTTPError as error:
            app.logger.error(f"Authentication failed. HTTP Status code {error.response.status_code}. Headers: {error.response.headers}")
            return jsonify({"status": "error", "code": error.response.status_code}), 500

        user = authenticate_user(untappd_access_token)
        access_token = create_access_token(identity=user.user_name)

        # Redirect user to frontend with JWT token in cookie
        response = make_response(redirect(f"{app.config['APP_DOMAIN']}", 301))
        response.set_cookie('jwt_token', access_token,
                            domain=app.config['DOMAIN_ROOT'])

        return response

    def authenticate_user(access_token: str):
        raw_user, response = untappd_api.user_info(access_token=access_token)
        user_id = raw_user['uid']

        # Check if user exist in database
        user = User.query.get(user_id)

        # Add if missing
        if user is None:
            user = add_user(raw_user, access_token)
            app.logger.info(f"Added token for user {user.user_name}")
        else:
            # Make sure token is up to date
            if user.access_token != access_token:
                user.access_token = access_token
                app.logger.info(f"Updated token for user {user.user_name}")
                db.session.commit()

        return user

    def add_user(raw_user, access_token: str) -> User:
        user = User(id=raw_user['uid'],
                    user_name=raw_user['user_name'],
                    first_name=raw_user['first_name'],
                    last_name=raw_user['last_name'],
                    avatar=raw_user['user_avatar'],
                    avatar_hd=raw_user['user_avatar_hd'],
                    total_badges=raw_user['stats']['total_badges'],
                    total_friends=raw_user['stats']['total_friends'],
                    total_checkins=raw_user['stats']['total_checkins'],
                    total_beers=raw_user['stats']['total_beers'],
                    access_token=access_token,
                    api_request_count=0)

        db.session.add(user)
        db.session.commit()

        return user

    def update_user(user, raw_user) -> User:
        user.first_name = raw_user['first_name']
        user.last_name = raw_user['last_name']
        user.avatar = raw_user['user_avatar']
        user.avatar_hd = raw_user['user_avatar_hd']
        user.total_badges = raw_user['stats']['total_badges']
        user.total_friends = raw_user['stats']['total_friends']
        user.total_checkins = raw_user['stats']['total_checkins']
        user.total_beers = raw_user['stats']['total_beers']

        db.session.commit()
        return user

    def add_beer(raw_beer, brewery: Brewery) -> Beer:
        beer = Beer(id=raw_beer['bid'],
                    name=raw_beer['beer_name'],
                    label=raw_beer['beer_label'],
                    rating=raw_beer['rating_score'],
                    abv=raw_beer['beer_abv'],
                    brewery=brewery,
                    style=raw_beer['beer_style'])

        db.session.add(beer)
        db.session.commit()

        return beer

    def add_brewery(raw_brewery) -> Brewery:
        brewery = Brewery(id=raw_brewery['brewery_id'],
                          name=raw_brewery['brewery_name'],
                          label=raw_brewery['brewery_label'],
                          country=raw_brewery['country_name'],
                          city=raw_brewery['location']['brewery_city'],
                          state=raw_brewery['location']['brewery_state'],
                          latitude=raw_brewery['location']['lat'],
                          longitude=raw_brewery['location']['lng'])

        db.session.add(brewery)
        db.session.commit()

        return brewery

    def add_venue(raw_venue) -> Venue:
        venue = Venue(id=raw_venue['venue_id'],
                      name=raw_venue['venue_name'],
                      country=raw_venue['location']['venue_country'],
                      city=raw_venue['location']['venue_city'],
                      state=raw_venue['location']['venue_state'],
                      latitude=raw_venue['location']['lat'],
                      longitude=raw_venue['location']['lng'])

        db.session.add(venue)
        db.session.commit()

        return venue

    @app.route('/v1/users/<string:username>')
    def get_user_details(username: str):
        user = get_user_from_db(username)

        if user:
            data = {
                "status": "success",
                "data": {
                    "user": user_schema.dump(user, many=False)[0]
                }
            }

            app.logger.info(f'Successfully returned user {username}')

            return jsonify(data), 200
        else:
            data = {
                "status": "fail",
                "message": "User does not exist"
            }

            app.logger.info(f'Request for non-existing user {username}')

            return jsonify(data), 404

    @app.route('/v1/users/<string:username>/checkins')
    def get_user_checkins(username: str):
        checkins = Checkin.query.filter(func.lower(
            Checkin.user_name) == func.lower(username)).all()

        data = {
            "status": "success",
            "data": {
                "checkins": checkins_schema.dump(checkins)
            }
        }

        return jsonify(data), 200

    def get_user_from_db(username: str):
        return User.query.filter(func.lower(User.user_name) == func.lower(username)).first()

    def contains(list, filter):
        for x in list:
            if filter(x):
                return True
        return False

    @app.route('/v1/users/<string:username>/countries')
    def get_user_countries(username: str):
        user = get_user_from_db(username)
        checkins = Checkin.query.filter_by(user=user).options(
            db.joinedload(Checkin.beer).joinedload(Beer.brewery)).all()

        countries = []

        with open('app/map.json') as f:
            data = json.load(f)
            countryData = data['objects']['units']['geometries']

        for checkin in checkins:
            country = checkin.beer.brewery.country
            original_country = country

            for x in countries:
                if x['name'] == country:
                    x['count'] += 1
                    x['beers'].append(checkin_schema.dump(checkin).data)
                    break
            else:
                country_code = get_country_code(original_country).upper()

                if not contains(countryData, lambda x: x['properties']['iso_a2'] == country_code):
                    app.logger.error(f"Missing map code for country {country}")

                x = {'name': country, 'count': 1, 'beers': [],
                     'code': country_code}
                x['beers'].append(checkin_schema.dump(checkin).data)

                countries.append(x)

        for country in countries:
            scores = []

            for checkin in country['beers']:
                if checkin['rating'] != 0:
                    scores.append(checkin['rating'])

            if len(scores) > 0:
                country['average_rating'] = mean(scores)
            else:
                country['average_rating'] = 0

            del country['beers']

        data = {
            "status": "success",
            "data": {
                "countries": countries
            }
        }

        return jsonify(data), 200

    @app.route('/v1/users/<string:username>/countries/<string:country_code>')
    def get_user_country(username: str, country_code: str):
        country_code = country_code.lower()

        try:
            country_name = pycountry.countries.get(alpha_2=country_code.upper()).name
        except (AttributeError, KeyError):
            return jsonify(data = {"status": "error", "message": "Country not found"}), 404

        user = get_user_from_db(username)
        checkins = Checkin.query.filter_by(user=user).options(
            db.joinedload(Checkin.beer).joinedload(Beer.brewery)).all()

        count = 0
        ratings = []
        breweries = []

        for checkin in checkins:
            if country_code != get_country_code(checkin.beer.brewery.country):
                continue

            beer = checkin.beer
            brewery = beer.brewery
            count += 1
            ratings.append(checkin.rating)

            beer = beer_schema.dump(beer, many=False)[0]
            beer['userRating'] = checkin.rating
            beer['firstHad'] = checkin.first_had
            beer['count'] = checkin.count

            for x in breweries:
                if x['id'] == brewery.id:
                    x['count'] += 1
                    x['ratings'].append(checkin.rating)
                    x['beers'].append(beer)
                    break
            else:
                x = {
                    'id': brewery.id,
                    'count': 1,
                    'ratings': [checkin.rating],
                    'location': {
                        'lat': brewery.latitude,
                        'lon': brewery.longitude
                    },
                    'label': brewery.label,
                    'name': brewery.name,
                    'beers': [beer]
                }

                breweries.append(x)

        for brewery in breweries:
            brewery['averageRating'] = safe_mean(brewery['ratings'])

            del brewery['ratings']

        data = {
            "status": "success",
            "data": {
                "count": count,
                "code": country_code,
                "name": country_name,
                "averageRating": safe_mean(ratings),
                "breweries": breweries
            }
        }

        return jsonify(data), 200

    def safe_mean(data):
        data = [x for x in data if x != 0]
        return mean(data) if len(data) > 0 else 0

    # Needed to map some country names not adhering to ISO
    COUNTRY_CODE_MAPPING_TABLE = {
        'Bolivia': 'bo',
        'China / People\'s Republic of China': 'cn',
        'England': 'gb',
        'Ivory Coast': 'ci',
        'Czech Republic': 'cz',
        'Democratic Republic of the Congo': 'cd',
        'Kosovo': 'xk',
        'Laos': 'la',
        'Republic of Macedonia': 'mk',
        'Macau': 'mo',
        'Moldova': 'md',
        'Palestinian Territories': 'ps',
        'Principality of Monaco': 'mc',
        'Northern Ireland': 'gb',
        'Republic of Congo': 'cg',
        'Russia': 'ru',
        'Scotland': 'gb',
        'South Korea': 'kr',
        'Surinam': 'sr',
        'Taiwan': 'tw',
        'Tanzania': 'tz',
        'United States Virgin Islands': 'vi',
        'Venezuela': 've',
        'Vietnam': 'vn',
        'Wales': 'gb',
    }

    def get_country_code(country: str):

        if COUNTRY_CODE_MAPPING_TABLE.get(country):
            return COUNTRY_CODE_MAPPING_TABLE.get(country)

        try:
            return pycountry.countries.get(name=country).alpha_2.lower()
        except (KeyError, AttributeError):
            app.logger.error(f'Missing code for country: {country}')
            return ""

    @app.route('/v1/users/<string:username>/dayofweek')
    def get_dayofweek_for_username(username: str):
        user = get_user_from_db(username)
        checkins = Checkin.query.filter_by(user=user).all()

        weekdays = []

        for checkin in checkins:
            weekday = checkin.first_had.isoweekday()
            rating = checkin.rating

            for x in weekdays:
                if x['weekday'] == weekday:
                    x['count'] += 1
                    x['ratings'].append(rating)
                    break
            else:
                x = {'weekday': weekday, 'count': 1, 'ratings': [rating]}

                weekdays.append(x)

        for weekday in weekdays:
            weekday['averageRating'] = safe_mean(weekday['ratings'])
            del weekday['ratings']

        data = {
            "status": "success",
            "data": {
                "weekdays": weekdays
            }
        }

        return jsonify(data), 200

    @app.route('/v1/users/<string:username>/timeofday')
    def get_timeofday_for_username(username: str):
        user = get_user_from_db(username)
        checkins = Checkin.query.filter_by(user=user).all()

        hours = []

        for checkin in checkins:
            hour = checkin.first_had.time().hour
            rating = checkin.rating

            for x in hours:
                if x['hour'] == hour:
                    x['count'] += 1
                    x['ratings'].append(rating)
                    break
            else:
                x = {'hour': hour, 'count': 1, 'ratings': [rating]}

                hours.append(x)

        for hour in hours:
            hour['averageRating'] = safe_mean(hour['ratings'])
            del hour['ratings']

        data = {
            "status": "success",
            "data": {
                "hours": hours
            }
        }

        return jsonify(data), 200

    @app.route('/v1/users/<string:username>/month')
    def get_month_for_username(username: str):
        user = get_user_from_db(username)
        checkins = Checkin.query.filter_by(user=user).all()

        months = []

        for checkin in checkins:
            month = checkin.first_had.month
            rating = checkin.rating

            for x in months:
                if x['month'] == month:
                    x['count'] += 1
                    x['ratings'].append(rating)
                    break
            else:
                x = {'month': month, 'count': 1, 'ratings': [rating]}

                months.append(x)

        for month in months:
            month['averageRating'] = safe_mean(month['ratings'])
            del month['ratings']

        data = {
            "status": "success",
            "data": {
                "months": months
            }
        }

        return jsonify(data), 200

    @app.route('/v1/users/<string:username>/year')
    def get_year_for_username(username: str):
        user = get_user_from_db(username)
        checkins = Checkin.query.filter_by(user=user).all()

        years = []

        for checkin in checkins:
            year = checkin.first_had.year
            rating = checkin.rating

            for x in years:
                if x['year'] == year:
                    x['count'] += 1
                    x['ratings'].append(rating)
                    break
            else:
                x = {'year': year, 'count': 1, 'ratings': [rating]}

                years.append(x)

        for year in years:
            year['averageRating'] = safe_mean(year['ratings'])
            del year['ratings']

        data = {
            "status": "success",
            "data": {
                "years": years
            }
        }

        return jsonify(data), 200

    @app.route('/v1/users/<string:username>/graph')
    def get_graph_for_username(username: str):
        user = get_user_from_db(username)
        checkins = Checkin.query.filter_by(user=user).order_by(Checkin.first_had.asc()).all()

        dates = []
        sum = 0

        for checkin in checkins:
            date = f'{checkin.first_had.year}/{checkin.first_had.month}/{checkin.first_had.day}'
            sum += 1

            for x in dates:
                if x['date'] == date:
                    x['count'] = sum
                    break
            else:
                x = {'date': date, 'count': sum}

                dates.append(x)

        data = {
            "status": "success",
            "data": {
                "dates": dates
            }
        }

        return jsonify(data), 200

    @socketio.on('update')
    def update_socketio(data):
        app.logger.info(f"SocketIO: Update")
        # Authenticate user
        # TODO: Error check
        user = decode_token(data['token'])['identity']
        username = data['username']

        if user:
            token_user = get_user_from_db(user)
            access_token = token_user.access_token

            app.logger.info(f"Updating user {username} using {user}")

            raw_user, _ = untappd_api.user_info(
                username=username, access_token=access_token)
            user = get_user_from_db(username)

            if user is None:
                user = add_user(raw_user, "")
            else:
                user = update_user(user, raw_user)

            beer_count = user.total_beers

            for offset in range(0, beer_count, 50):
                if not update_from_offset(offset, beer_count, username, access_token, user):
                    break

            user.last_update = datetime.datetime.utcnow()
            print(user.last_update)
            db.session.commit()

            socketio.emit('update:finished', {'finished': True})
            app.logger.info(f"SocketIO: Finished")
            socketio.sleep(0)

    def update_from_offset(offset, beer_count, username, access_token, user):
        socketio.emit('update:progress', {
                      'progress': offset, 'total': beer_count})
        app.logger.info(f"SocketIO: Progress ({offset}/{beer_count})")
        socketio.sleep(0)

        try:
            beers_add, _ = untappd_api.user_beers(
                username, offset, 50, access_token)
            beers = beers_add['items']
        except:
            return False

        for raw_beer in beers:
            if not handle_beer(raw_beer, user):
                return False

        return True

    def handle_beer(raw_beer, user):
        brewery = Brewery.query.filter_by(
            id=raw_beer['brewery']['brewery_id']).first()

        if brewery is None:
            brewery = add_brewery(raw_beer['brewery'])

        beer = Beer.query.filter_by(
            id=raw_beer['beer']['bid']).first()

        if beer is None:
            beer = add_beer(raw_beer['beer'], brewery)

        checkin = Checkin.query.filter_by(
            id=raw_beer['first_checkin_id']).first()

        if checkin is None:
            # Format: Sat, 04 Aug 2018 14:44:31 -0400
            first_had = datetime.datetime.strptime(
                raw_beer['first_had'], '%a, %d %b %Y %H:%M:%S %z')
            first_had = first_had.replace(tzinfo=None)

            checkin = Checkin(id=raw_beer['first_checkin_id'],
                              beer=beer,
                              user=user,
                              count=raw_beer['count'],
                              rating=raw_beer['rating_score'],
                              first_had=first_had)

            db.session.add(checkin)
            db.session.commit()
        else:
            return False
        return True

    return app
