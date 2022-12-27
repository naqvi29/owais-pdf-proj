from flask import Flask, render_template, session, redirect, url_for, jsonify, request
import logging
import os
import stripe
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from os.path import join, dirname, realpath

stripe_keys = {
  'secret_key': 'sk_test_51JmHU9ApaRg7P8yR8LoM8vj0MOKmEFEsdF8GM3nvf0ptNOUveSERzo8tcYdw2SKkcn1IeToUUDePOuDBjwllRgEi00JOR2lDKA',
  'publishable_key': 'pk_test_51JmHU9ApaRg7P8yRAqT56Mr1AOiTHGp5LEMmcZE9hfJLLqkjlZPpJARsJ11iHP17XsUuDDWalaToyHpocprJacqU00xoXC6R6I'
}

stripe.api_key = stripe_keys['secret_key']

UPLOAD_FOLDER = join(dirname(realpath(__file__)), 'static/profile-pics/')

app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'zoomcare'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# app.config['MYSQL_PORT'] = 3308
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# configure secret key for session protection)
app.secret_key = '_5#y2L"F4Q8z\n\xec]/'

mysql = MySQL(app)

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS 

@app.route('/')
def index():    
    if 'loggedin' in session:
        return render_template('index.html',loggedin=True)
    else:
        return render_template('index.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get("password")
        
        cursor = mysql.connection.cursor()
        cursor.execute('Select * from users where email=%s;',[email])    
        user = cursor.fetchone()
        if not user:
            return render_template("login.html", error="Invalid Email!")
        if password != user['password']:
            return render_template("login.html", error="Invalid Password!")
        session['loggedin'] = True
        session['userid'] = str(user["id"])
        session['name'] = user["name"]
        session['email'] = user["email"]
        session['type'] = user['type']
        session['pic'] = user['pic']
        session['password'] = user['password']
        return redirect(url_for("dashboard"))

    return render_template('login.html')

@app.route("/logout")
def logout():
    try:
        if 'loggedin' in session:
            session.pop('loggedin', None)
            session.pop('userid', None)
            session.pop('name', None)
            session.pop('email', None)
            session.pop('type', None)
            session.pop('pic', None)
            session.pop('password', None)
        return redirect(url_for('index'))
    except Exception as e:
        return str(e)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        image = request.files["pic"]
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(
                    os.path.join(UPLOAD_FOLDER, filename))
            cursor = mysql.connection.cursor()
            cursor.execute('Select * from users where email=%s;',[email])    
            user = cursor.fetchone()
            if user:
                return render_template("register.html", error="Account already exist!")
            cursor.execute('INSERT into users (name,email,password,type,pic) VALUES (%s,%s,%s,"user",%s);',(name,email,password,filename))
            mysql.connection.commit()
        else:
            return render_template("register.html", error="Invalid Profile Picture!")

        return render_template("login.html",success=True)


    return render_template('register.html')

@app.route('/select-plan/<int:id>', methods=['GET','POST'])
def select_plan(id):
    if id == 1:
        price = "19"
        plan = "starter"
    elif id == 2:
        price = "29"
        plan = "basic"
    elif id == 3:
        price = "49"
        plan = "professional"
    elif id == 4:
        price = "99"
        plan = "ultra"
    return render_template('checkout.html', price=price, plan=plan, key=stripe_keys['publishable_key'], amount=float(price)*100)
    
@app.route('/charge', methods=['POST'])
def charge():
    # Amount in cents
    # amount = 500
    amount = float(request.form.get(amount))

    customer = stripe.Customer.create(
        email='customer@example.com',
        source=request.form['stripeToken']
    )

    charge = stripe.Charge.create(
        customer=customer.id,
        amount=amount,
        currency='usd',
        description='Flask Charge'
    )

    return render_template('charge.html', amount=amount)

# ------------------- DASHBOARD ----------------------
@app.route("/dashboard")
def dashboard():
    if 'loggedin' in session:
        user = {"id":session['userid'],"name":session['name'],"email":session['email'],"type":session['type'],"pic":session['pic']}
        return render_template("dashboard-index.html",user=user)
    else:
        return redirect(url_for('login'))

@app.route("/account", methods=['GET','POST'])
def account():
    if 'loggedin' in session:
        if request.method == 'POST':
            name = request.form.get("name")
            email = request.form.get("email")
            password = request.form.get("password")
            image = request.files["pic"]
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image.save(
                        os.path.join(UPLOAD_FOLDER, filename))
                cursor = mysql.connection.cursor()
                cursor.execute('UPDATE USERS SET name=%s,email=%s,password=%s,pic=%s where id=%s;',(name,email,password,filename,session['userid']))
                mysql.connection.commit()
                session['pic'] = filename
            else:
                cursor = mysql.connection.cursor()
                cursor.execute('UPDATE USERS SET name=%s,email=%s,password=%s where id=%s;',(name,email,password,session['userid']))
                mysql.connection.commit()
            
            session['name'] = name
            session['email'] = email
            session['password'] = password
            return redirect(url_for("account"))

        user = {"id":session['userid'],"name":session['name'],"email":session['email'],"type":session['type'],"pic":session['pic'],"password":session['password']}
        return render_template("dashboard-account.html",user=user)
    else:
        return redirect(url_for('login'))

# ------------------- DASHBOARD ----------------------

if __name__ == '__main__':
    app.run(debug=True)