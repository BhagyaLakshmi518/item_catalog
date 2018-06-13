from flask import Flask, render_template
from flask import request, redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from jewel_db import Base, User, Jewellery, JewelItem
from flask import session as login_session
import random
import string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Jewellery Application"


''' Connect to Database and create database session'''
engine = create_engine('sqlite:///Jewellery.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


''' Create anti-forgery state token'''


@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    ''' return "The current session state is %s" % login_session['state']'''
    print("logHTML")
    return render_template('login.html', STATE=state)

'''
gconnect check client access token with project json file,
and validate user Login
'''


@app.route('/gconnect', methods=['POST'])
def gconnect():
    ''' Validate state token'''
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    ''' Obtain authorization code'''
    code = request.data
    print("here")
    try:
        ''' Upgrade the authorization code into a credentials object'''
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    ''' Check that the access token is valid.'''
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    ''' If there was an error in the access token info, abort.'''
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    ''' Verify that the access token is used for the intended user.'''
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    ''' Verify that the access token is valid for this app.'''
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        print('already')
        response = make_response(json.dumps(
            'Current user is already connected.'
            ), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    ''' Store the access token in the session for later use.'''
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id
    ''' Get user info'''
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    ''' See if a user exists, if it doesn't make a new one '''
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


'''User Helper Functions'''


def createUser(login_session):
    session = DBSession()
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    session.close()
    return user.id


def getUserInfo(user_id):

    session = DBSession()
    user = session.query(User).filter_by(id=user_id).one()
    session.close()
    return user


def getUserID(email):
    try:
        session = DBSession()
        user = session.query(User).filter_by(email=email).one()
        session.close()
        return user.id
    except:
        return None


''' DISCONNECT - Revoke a current user's token and reset their login_session'''


@app.route('/logout')
def gdisconnect():
    ''' Only disconnect a connected user.'''
    access_token = login_session.get('access_token')
    print(access_token)
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        ''' Reset the user's sesson. '''
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        flash('Successfully Logged Out')
        return redirect('/')
    else:
        ''' For whatever reason, the given token was invalid. '''
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view Jewellery Information
@app.route('/jewellery/<int:jewel_id>/menu/JSON')
def restaurantMenuJSON(jewel_id):
    jewellery = session.query(Jewellery).filter_by(id=jewel_id).one()
    items = session.query(JewelItem).filter_by(
        jewel_id=jewel_id).all()
    return jsonify(MenuItems=[i.serialize for i in items])


@app.route('/jewellery/<int:jewel_id>/menu/<int:menu_id>/JSON')
def menuItemJSON(jewel_id, menu_id):
    Menu_Item = session.query(JewelItem).filter_by(id=menu_id).one()
    return jsonify(Menu_Item=Menu_Item.serialize)


@app.route('/jewellery/JSON')
def restaurantsJSON():
    jewelleries = session.query(Jewellery).all()
    return jsonify(jewelleries=[r.serialize for r in jewelleries])


# Show all jewelleries
@app.route('/')
@app.route('/jewellery/')
def showJewellery():
    session = DBSession()
    jewelleries = session.query(Jewellery).order_by(asc(Jewellery.name))
    session.close()
    return render_template('jewelleries.html', jewelleries=jewelleries)

# Create a new jewellery


@app.route('/jewellery/new/', methods=['GET', 'POST'])
def newJewellery():
    session = DBSession()
    if 'username' not in login_session:
        print("logged in")
        return redirect('/login')
    if request.method == 'POST':
        newJewellery = Jewellery(
            name=request.form['name'], user_id=login_session['user_id'])
        session.add(newJewellery)
        flash('New Jewellery %s Successfully Created' % newJewellery.name)
        session.commit()
        return redirect(url_for('showJewellery'))
    else:
        return render_template('newJewellery.html')
    session.close()
# Edit a jewellery


@app.route('/jewellery/<int:jewel_id>/edit/', methods=['GET', 'POST'])
def editJewellery(jewel_id):
    session = DBSession()
    if 'username' not in login_session:
        redirect('/login')
    editedRestaurant = session.query(
        Jewellery).filter_by(id=jewel_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedRestaurant.name = request.form['name']
            flash('Jewellery Successfully Edited %s' % editedRestaurant.name)
            print(editedRestaurant.name)
            session.add(editedRestaurant)
            session.commit()
            return redirect(url_for('showJewellery'))
    else:
        return render_template('editJewellery.html', jewellery=editedRestaurant)
    session.close()

# Delete a jewellery
@app.route('/jewellery/<int:jewel_id>/delete/', methods=['GET', 'POST'])
def deleteJewellery(jewel_id):
    session = DBSession()
    if 'username' not in login_session:
        return redirect('/login')
    restaurantToDelete = session.query(
        Jewellery).filter_by(id=jewel_id).one()
    if request.method == 'POST':
        session.delete(restaurantToDelete)
        flash('%s Successfully Deleted' % restaurantToDelete.name)
        session.commit()
        return redirect(url_for('showJewellery', jewel_id=jewel_id))
    else:
        return render_template('deleteJewellery.html', jewellery=restaurantToDelete)
    session.close()
# Show a jewellery menu


@app.route('/jewellery/<int:jewel_id>/')
@app.route('/jewellery/<int:jewel_id>/menu/')
def showMenu(jewel_id):
    session = DBSession()
    jewellery = session.query(Jewellery).filter_by(id=jewel_id).one()
    items = session.query(JewelItem).filter_by(
        jewel_id=jewel_id).all()
    return render_template('menu.html', items=items, jewellery=jewellery)
    session.close()

# Create a new menu item
@app.route('/jewellery/<int:jewel_id>/menu/new/', methods=['GET', 'POST'])
def newMenuItem(jewel_id):
    session = DBSession()
    if 'username' not in login_session:
        return redirect('/login')
    jewellery = session.query(Jewellery).filter_by(id=jewel_id).one()
    if request.method == 'POST':
        newItem = JewelItem(name=request.form['name'], description=request.form['description'], price=request.form[
                           'price'], jewel_id=jewel_id, user_id=jewellery.user_id)
        session.add(newItem)
        session.commit()
        flash('New Menu %s Item Successfully Created' % (newItem.name))
        return redirect(url_for('showMenu', jewel_id=jewel_id))
    else:
        return render_template('newmenuitem.html', jewel_id=jewel_id)
    session.close()
# Edit a menu item


@app.route('/jewellery/<int:jewel_id>/menu/<int:menu_id>/edit', methods=['GET', 'POST'])
def editMenuItem(jewel_id, menu_id):
    session = DBSession()
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(JewelItem).filter_by(id=menu_id).one()
    jewellery = session.query(Jewellery).filter_by(id=jewel_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        session.add(editedItem)
        session.commit()
        session.close()
        flash('Menu Item Successfully Edited')
        return redirect(url_for('showMenu', jewel_id=jewel_id))
    else:
        return render_template('editmenuitem.html', jewel_id=jewel_id, menu_id=menu_id, item=editedItem)
    

# Delete a menu item
@app.route('/jewellery/<int:jewel_id>/menu/<int:menu_id>/delete', methods=['GET', 'POST'])
def deleteMenuItem(jewel_id, menu_id):
    session = DBSession()
    if 'username' not in login_session:
        return redirect('/login')
    jewellery = session.query(Jewellery).filter_by(id=jewel_id).one()
    itemToDelete = session.query(JewelItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Menu Item Successfully Deleted')
        return redirect(url_for('showMenu', jewel_id=jewel_id))
    else:
        return render_template('deleteMenuItem.html', item=itemToDelete)
    session.close()

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=3000)
