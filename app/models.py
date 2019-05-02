import datetime

from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy
from marshmallow import fields

db = SQLAlchemy()
ma = Marshmallow()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(80), unique=True)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    avatar = db.Column(db.String(200))
    avatar_hd = db.Column(db.String(200))
    total_badges = db.Column(db.Integer)
    total_friends = db.Column(db.Integer)
    total_checkins = db.Column(db.Integer)
    total_beers = db.Column(db.Integer)
    access_token = db.Column(db.String(200))
    api_request_count = db.Column(db.Integer)
    last_update = db.Column(db.DateTime(timezone=False))

    def __init__(self,
                 id: int,
                 user_name: str,
                 first_name: str,
                 last_name: str,
                 avatar: str,
                 avatar_hd: str,
                 total_badges: int,
                 total_friends: int,
                 total_checkins: int,
                 total_beers: int,
                 access_token: str,
                 api_request_count: int):
        self.id = id
        self.user_name = user_name
        self.first_name = first_name
        self.last_name = last_name
        self.avatar = avatar
        self.avatar_hd = avatar_hd
        self.total_badges = total_badges
        self.total_friends = total_friends
        self.total_checkins = total_checkins
        self.total_beers = total_beers
        self.access_token = access_token
        self.api_request_count = api_request_count


class UserSchema(ma.Schema):
    class Meta:
        # Fields to expose
        fields = ('id', 'user_name', 'first_name', 'last_name', 'avatar',
                  'avatar_hd', 'total_badges', 'total_friends',
                  'total_checkins', 'total_beers', 'last_update')


user_schema = UserSchema()


class Friendship(db.Model):
    __tablename__ = 'friendships'

    hash = db.Column(db.String(80), primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user1 = db.relationship('User', foreign_keys=[user1_id])
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user2 = db.relationship('User', foreign_keys=[user2_id])

    def __init__(self,
                 hash: str,
                 user1: User,
                 user2: User):
        self.hash = hash
        self.user1 = user1
        self.user2 = user2


class Brewery(db.Model):
    __tablename__ = 'breweries'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    label = db.Column(db.String(200))
    country = db.Column(db.String(80))
    city = db.Column(db.String(80))
    state = db.Column(db.String(80))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    def __init__(self, id, name, label, country, city, state, latitude, longitude):
        self.id = id
        self.name = name
        self.label = label
        self.country = country
        self.city = city
        self.state = state
        self.latitude = latitude
        self.longitude = longitude


class BrewerySchema(ma.Schema):
    class Meta:
        # Fields to expose
        fields = ('id', 'name', 'label', 'country', 'city', 'state', 'latitude', 'longitude')


class Venue(db.Model):
    __tablename__ = 'venues'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    country = db.Column(db.String(80))
    city = db.Column(db.String(80))
    state = db.Column(db.String(80))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    def __init__(self, id, name, country, city, state, latitude, longitude):
        self.id = id
        self.name = name
        self.country = country
        self.city = city
        self.state = state
        self.latitude = latitude
        self.longitude = longitude


class VenueSchema(ma.Schema):
    class Meta:
        # Fields to expose
        fields = ('id', 'name', 'country', 'city', 'state', 'latitude', 'longitude')


class Beer(db.Model):
    __tablename__ = 'beers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    label = db.Column(db.String(200))
    rating = db.Column(db.Float)
    abv = db.Column(db.Float)
    brewery_id = db.Column(db.Integer, db.ForeignKey('breweries.id'), nullable=False)
    brewery = db.relationship('Brewery', backref=db.backref('beers', lazy=True))
    style = db.Column(db.String(80))

    def __init__(self, id, name, label, rating, abv, brewery, style):
        self.id = id
        self.name = name
        self.label = label
        self.rating = rating
        self.abv = abv
        self.brewery = brewery
        self.style = style


class BeerSchema(ma.Schema):
    brewery = fields.Nested('BrewerySchema')

    class Meta:
        # Fields to expose
        fields = ('id', 'name', 'label', 'rating', 'abv', 'style')


beer_schema = BeerSchema()


class Checkin(db.Model):
    __tablename__ = 'checkins'

    id = db.Column(db.Integer, primary_key=True)
    beer_id = db.Column(db.Integer, db.ForeignKey('beers.id'), nullable=False)
    beer = db.relationship('Beer', backref=db.backref('checkins', lazy=True))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('checkins', lazy=True))
    count = db.Column(db.Integer)
    rating = db.Column(db.Float)
    first_had = db.Column(db.DateTime(timezone=False))

    def __init__(self, id, beer, user, count, rating, first_had):
        self.id = id
        self.beer = beer
        self.user = user
        self.count = count
        self.rating = rating
        self.first_had = first_had


class CheckinSchema(ma.Schema):
    beer = fields.Nested('BeerSchema')

    class Meta:
        fields = ('id', 'beer', 'user', 'count', 'rating', 'first_had')


checkin_schema = CheckinSchema()
checkins_schema = CheckinSchema(many=True)


class Badge(db.Model):
    __tablename__ = 'badges'

    id = db.Column(db.Integer, primary_key=True)
    badge_image_sm = db.Column(db.String(200))
    badge_image_md = db.Column(db.String(200))
    badge_image_lg = db.Column(db.String(200))
