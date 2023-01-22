from flask import Flask, render_template, session, redirect, url_for, jsonify, request, send_file
import os
import stripe
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from os.path import join, dirname, realpath
import json
import datetime
import requests

stripe_keys = {
  'secret_key': 'sk_test_51JmHU9ApaRg7P8yR8LoM8vj0MOKmEFEsdF8GM3nvf0ptNOUveSERzo8tcYdw2SKkcn1IeToUUDePOuDBjwllRgEi00JOR2lDKA',
  'publishable_key': 'pk_test_51JmHU9ApaRg7P8yRAqT56Mr1AOiTHGp5LEMmcZE9hfJLLqkjlZPpJARsJ11iHP17XsUuDDWalaToyHpocprJacqU00xoXC6R6I'
}

stripe.api_key = stripe_keys['secret_key']

UPLOAD_FOLDER = join(dirname(realpath(__file__)), 'static/profile-pics/')
UPLOAD_FOLDER2 = join(dirname(realpath(__file__)), 'static/uploaded-pdfs/')
UPLOAD_FOLDER3 = join(dirname(realpath(__file__)), 'static/api-pdfs/')
UPLOAD_FOLDER4 = join(dirname(realpath(__file__)), 'static/doc-pdfs/')

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
        if user['status'] == "active":
            session['loggedin'] = True
            session['userid'] = str(user["id"])
            session['name'] = user["name"]
            session['email'] = user["email"]
            session['type'] = user['type']
            session['pic'] = user['pic']
            session['password'] = user['password']
            session['auto_del'] = user['auto_del']
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Your Account is inactive!")


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
            cursor.execute('INSERT into users (name,email,password,type,pic,status) VALUES (%s,%s,%s,"user",%s,"active");',(name,email,password,filename))
            mysql.connection.commit()
        else:
            return render_template("register.html", error="Invalid Profile Picture!")

        return render_template("login.html",success=True)


    return render_template('register.html')

@app.route('/select-plan/<int:id>', methods=['GET','POST'])
def select_plan(id):
    # demo 
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
        if session['type']=="admin":
        
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT COUNT(*) FROM pdf_logs;')
            pdf_logs = cursor.fetchone()['COUNT(*)']
            cursor.execute('SELECT COUNT(*) FROM contract_logs;')
            contract_logs = cursor.fetchone()['COUNT(*)']
            cursor.execute('SELECT COUNT(*) FROM users where type="user";')
            users = cursor.fetchone()['COUNT(*)']
            auto_del = session['auto_del']
            user = {"id":session['userid'],"name":session['name'],"email":session['email'],"type":session['type'],"pic":session['pic']}
            return render_template("dashboard-index.html",user=user,pdf_logs=pdf_logs,contract_logs=contract_logs,users=users,auto_del=auto_del,admin=True)
        else:
        
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT COUNT(*) FROM pdf_files where userid=%s;',[session['userid']])
            pdf_files = cursor.fetchone()['COUNT(*)']
            cursor.execute('SELECT COUNT(*) FROM api_pdfs where userid=%s;',[session['userid']])
            api_pdfs = cursor.fetchone()['COUNT(*)']
            cursor.execute('SELECT COUNT(*) FROM form_entries where user_id=%s;',[session['userid']])
            form_entries = cursor.fetchone()['COUNT(*)']
            cursor.execute('SELECT COUNT(*) FROM form_entries where user_id=%s and status="completed";',[session['userid']])
            completed_form_entries = cursor.fetchone()['COUNT(*)']
            
            user = {"id":session['userid'],"name":session['name'],"email":session['email'],"type":session['type'],"pic":session['pic']}
            return render_template("dashboard-index.html",user=user,pdf_files=pdf_files,api_pdfs=api_pdfs,form_entries=form_entries,completed_form_entries=completed_form_entries)
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
            if session['type'] == "admin":
                auto_del = request.form.get("auto_del")
            else:
                auto_del = None
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image.save(
                        os.path.join(UPLOAD_FOLDER, filename))
                cursor = mysql.connection.cursor()
                
                if session['type'] == "admin":
                    cursor.execute('UPDATE USERS SET name=%s,email=%s,password=%s,pic=%s,auto_del=%s where id=%s;',(name,email,password,filename,auto_del,session['userid']))
                else:
                    cursor.execute('UPDATE USERS SET name=%s,email=%s,password=%s,pic=%s where id=%s;',(name,email,password,filename,session['userid']))
                mysql.connection.commit()
                session['pic'] = filename
            else:
                cursor = mysql.connection.cursor()
                if session['type'] == "admin":
                    cursor.execute('UPDATE USERS SET name=%s,email=%s,password=%s,auto_del=%s where id=%s;',(name,email,password,auto_del,session['userid']))
                else:
                    cursor.execute('UPDATE USERS SET name=%s,email=%s,password=%s where id=%s;',(name,email,password,session['userid']))
                mysql.connection.commit()
            
            session['name'] = name
            session['email'] = email
            session['password'] = password
            session['auto_del'] = auto_del
            return redirect(url_for("account"))

        user = {"id":session['userid'],"name":session['name'],"email":session['email'],"type":session['type'],"pic":session['pic'],"password":session['password'],"auto_del":session['auto_del']}
        if session['type'] == "admin":
            return render_template("dashboard-account.html",user=user,admin=True)
        else:
            return render_template("dashboard-account.html",user=user)
    else:
        return redirect(url_for('login'))

@app.route("/fill-contracts")
def fill_contracts():
    if 'loggedin' in session:
        user = {"id":session['userid'],"name":session['name'],"email":session['email'],"type":session['type'],"pic":session['pic']}
        return render_template("dashboard-fill-contracts.html",user=user)
    else:
        return redirect(url_for('login'))

@app.route("/select-form/<int:form_id>", methods=['GET','POST'])
def select_form(form_id):
    if 'loggedin' in session:
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * from forms where id=%s;',[form_id])
        if form_id==1:
            form = cursor.fetchone()
            cursor.execute('SELECT * from form_entries where form_id=%s and user_id=%s',[form_id,session['userid']])
            entry = cursor.fetchone()
            
            user = {"id":session['userid'],"name":session['name'],"email":session['email'],"type":session['type'],"pic":session['pic']}
            if entry:
                data = json.loads(entry['data'])
                entry.update({'data':data})
                # return jsonify({"entry":entry})
                return render_template("contract1.html",user=user,form=form,entry=entry)
            else:
                return render_template("contract1.html",user=user,form=form,entry=None)
        if form_id==2:
            form = cursor.fetchone()
            cursor.execute('SELECT * from form_entries where form_id=%s and user_id=%s',[form_id,session['userid']])
            entry = cursor.fetchone()
            
            user = {"id":session['userid'],"name":session['name'],"email":session['email'],"type":session['type'],"pic":session['pic']}
            if entry:
                data = json.loads(entry['data'])
                entry.update({'data':data})
                # return jsonify({"entry":entry})
                return render_template("contract2.html",user=user,form=form,entry=entry)
            else:
                return render_template("contract2.html",user=user,form=form,entry=None)
    else:
        return redirect(url_for('login'))

@app.route("/save-form/<int:form_id>" ,methods=['POST'])
def save_form(form_id):
    if 'loggedin' in session:
        
        date = datetime.datetime.now().strftime("%B %d, %Y")
        form_completed = False
        if form_id == 1:
            # COMPANY ONE 
            company_name = request.form.get("NAME_OF_COMPANY_ONE")
            company_type = request.form.get("TYPE_OF_COMPANY_ONE")
            registration_number = request.form.get("COMPANY_ONE_REGISTRATION_NUMBER")
            authority = request.form.get("AUTHORITY_ONE_NAME")
            office_address = request.form.get("AUTHORITY_ONE_OFFICE_ADDRESS")
            person_title = request.form.get("TITLE_OF_PERSON_REPRESENTING_THE_AUTHORITY_ONE")
            person_name = request.form.get("NAME_OF_PERSON_REPRESENTING_THE_AUTHORITY_ONE")
            country = request.form.get("COUNTRY_OF_NATIONALITY_AUTHORITY_ONE")
            passport_no = request.form.get("PASSPORT_NO_AUTHORITY_ONE")
            # COMPANY TWO
            company_name_2 = request.form.get("NAME_OF_COMPANY_TWO")
            company_type_2 = request.form.get("TYPE_OF_COMPANY_TWO")
            registration_no_2 = request.form.get("COMPANY_TWO_REGISTRATION_NUMBER")
            authority_2 = request.form.get("AUTHORITY_TWO_NAME")
            office_address_2 = request.form.get("AUTHORITY_TWO_OFFICE_ADDRESS")
            person_title_2 = request.form.get("TITLE_OF_PERSON_REPRESENTING_THE_AUTHORITY_TWO")
            person_name_2 = request.form.get("NAME_OF_PERSON_REPRESENTING_THE_AUTHORITY_TWO")
            country_2 = request.form.get("COUNTRY_OF_NATIONALITY_AUTHORITY_TWO")
            passport_no_2 = request.form.get("PASSPORT_NO_AUTHORITY_TWO")
            # OBJECTIVES
            business_description = request.form.get("SERVICES_FIRSTPARTY_TO_SECOND_PARTY")
            business_description_2 = request.form.get("SERVICES_SECOND_PARTY_TO_FIRSTPARTY")
            purpose_JV = ""
            object_description_2 = ""
            object_description = ""
            time_period = ""
            emirate = ""
            day_of = ""

            # SIGNATURES
            signature_1 = request.form.get("COMPANY_ONE_NAME_OF_SIGNATORY")
            signature_2 = request.form.get("COMPANY_TWO_NAME_OF_SIGNATORY")
            
            dict = {
                "NAME_OF_COMPANY_ONE" : request.form.get("NAME_OF_COMPANY_ONE") ,
                "TYPE_OF_COMPANY_ONE" : request.form.get("TYPE_OF_COMPANY_ONE") ,
                "COMPANY_ONE_REGISTRATION_NUMBER" : request.form.get("COMPANY_ONE_REGISTRATION_NUMBER") ,
                "AUTHORITY_ONE_NAME" : request.form.get("AUTHORITY_ONE_NAME") ,
                "AUTHORITY_ONE_OFFICE_ADDRESS" : request.form.get("AUTHORITY_ONE_OFFICE_ADDRESS") ,
                "TITLE_OF_PERSON_REPRESENTING_THE_AUTHORITY_ONE" : request.form.get("TITLE_OF_PERSON_REPRESENTING_THE_AUTHORITY_ONE") ,
                "NAME_OF_PERSON_REPRESENTING_THE_AUTHORITY_ONE" : request.form.get("NAME_OF_PERSON_REPRESENTING_THE_AUTHORITY_ONE") ,
                "COUNTRY_OF_NATIONALITY_AUTHORITY_ONE" : request.form.get("COUNTRY_OF_NATIONALITY_AUTHORITY_ONE") ,
                "PASSPORT_NO_AUTHORITY_ONE" : request.form.get("PASSPORT_NO_AUTHORITY_ONE") ,
                "NAME_OF_COMPANY_TWO" : request.form.get("NAME_OF_COMPANY_TWO") ,
                "TYPE_OF_COMPANY_TWO" : request.form.get("TYPE_OF_COMPANY_TWO") ,
                "COMPANY_TWO_REGISTRATION_NUMBER" : request.form.get("COMPANY_TWO_REGISTRATION_NUMBER") ,
                "AUTHORITY_TWO_NAME" : request.form.get("AUTHORITY_TWO_NAME") ,
                "AUTHORITY_TWO_OFFICE_ADDRESS" : request.form.get("AUTHORITY_TWO_OFFICE_ADDRESS") ,
                "TITLE_OF_PERSON_REPRESENTING_THE_AUTHORITY_TWO" : request.form.get("TITLE_OF_PERSON_REPRESENTING_THE_AUTHORITY_TWO") ,
                "NAME_OF_PERSON_REPRESENTING_THE_AUTHORITY_TWO" : request.form.get("NAME_OF_PERSON_REPRESENTING_THE_AUTHORITY_TWO") ,
                "COUNTRY_OF_NATIONALITY_AUTHORITY_TWO" : request.form.get("COUNTRY_OF_NATIONALITY_AUTHORITY_TWO") ,
                "PASSPORT_NO_AUTHORITY_TWO" : request.form.get("PASSPORT_NO_AUTHORITY_TWO") ,
                "SERVICES_FIRSTPARTY_TO_SECOND_PARTY" : request.form.get("SERVICES_FIRSTPARTY_TO_SECOND_PARTY") ,
                "SERVICES_SECOND_PARTY_TO_FIRSTPARTY" : request.form.get("SERVICES_SECOND_PARTY_TO_FIRSTPARTY") ,
                "COMPANY_ONE_NAME_OF_SIGNATORY" : request.form.get("COMPANY_ONE_NAME_OF_SIGNATORY") ,
                "COMPANY_TWO_NAME_OF_SIGNATORY" : request.form.get("COMPANY_TWO_NAME_OF_SIGNATORY")
            }
            data = json.dumps(dict)   
            cursor = mysql.connection.cursor() 
            cursor.execute("SELECT * from form_entries where user_id=%s and form_id=%s;",[session['userid'],form_id])
            exist = cursor.fetchone()
            if exist:
                cursor.execute("DELETE from form_entries where id=%s",[exist['id']])            
                mysql.connection.commit()
            cursor.execute('INSERT into form_entries (form_id,user_id,data,status) VALUES (%s,%s,%s,%s);',(form_id,session['userid'],data,"pending"))
            mysql.connection.commit()

            # now hit api 
            data = {
                "company_name":company_name,
                "company_type":company_type,
                "registration_number":registration_number,
                "authority":authority,
                "office_address":office_address,
                "person_title":person_title,
                "person_name":person_name,
                "country":country,
                "passport_no":passport_no,
                "company_name_2":company_name_2,
                "company_type_2": company_type_2,
                "registration_no_2":registration_no_2,
                "authority_2":authority_2,
                "office_address_2":office_address_2,
                "person_title_2":person_title_2,
                "person_name_2":person_name_2,
                "country_2":country_2,
                "passport_no_2":passport_no_2,
                "business_description":business_description,
                "business_description_2":business_description_2,
                "purpose_JV":purpose_JV,
                "object_description_2":object_description_2,
                "object_description":object_description,
                "time_period":time_period,
                "emirate":emirate,
                "day_of":day_of,
                "signature_1":signature_1,
                "signature_2":signature_2
            }
            response = requests.post("http://3.8.200.254/api/v1/jv_agreement", json=data)

            if response.status_code == 200:
                filename = "jv_agreement.pdf"
                with open(os.path.join(UPLOAD_FOLDER4,filename), "wb") as pdf_file:
                    pdf_file.write(response.content)
                    print("PDF saved successfully.")
                
                cursor.execute('INSERT into contract_pdfs (userid,formid,filename,date_time) VALUES (%s,%s,%s,%s);',(session['userid'],form_id,filename,date))
                mysql.connection.commit()
            else:
                print("Error with status code:", response.status_code)

            # --
            
            cursor.execute('UPDATE form_entries SET status="completed" where user_id=%s and form_id=%s;',[session['userid'],form_id])            
            mysql.connection.commit()

            
        elif form_id == 2:
            # PERSONAL INFORMATION 
            name = request.form.get("NAME")
            country = request.form.get("COUNTRY")
            passport = request.form.get("PASSPORT_NO")
            id_no = request.form.get("RESIDENT_EMIRATES_ID_NO")
            plate_no = request.form.get("TRAFFIC_PLATE_NO")
            emirate = id_no
            # AUTHORIZER INFORMATIOn
            name_2 = request.form.get("AUTHORIZER_NAME")
            country_2 = request.form.get("AUTHORIZER_COUNTRY")
            passport_2 = request.form.get("AUTHORIZER_PASSPORT_NO")
            id_no_2 = request.form.get("AUTHORIZER_RESIDENT_EMIRATES_ID_NO")
            # VEHICLE INFORMATION
            TRAFFIC_PLATE_NO = request.form.get("TRAFFIC_PLATE_NO")
            vehicle_type = request.form.get("VEHICLE_TYPE")
            color = request.form.get("VEHICLE_COLOR")
            year = request.form.get("VEHICLE_YEAR")
            engine_no = request.form.get("ENGINE_NO")
            chassis_no = request.form.get("CHASSIS_NO")
            # SIGNATURES
            OWNER_NAME = request.form.get("OWNER_NAME")
            OWNER_SIGN = request.form.get("OWNER_SIGN")
            ATTORNEY_NAME = request.form.get("ATTORNEY_NAME")
            ATTORNEY_SIGN = request.form.get("ATTORNEY_SIGN")

            dict = {
                "NAME" : request.form.get("NAME") ,
                "COUNTRY" : request.form.get("COUNTRY") ,
                "PASSPORT_NO" : request.form.get("PASSPORT_NO") ,
                "RESIDENT_EMIRATES_ID_NO" : request.form.get("RESIDENT_EMIRATES_ID_NO") ,
                "TRAFFIC_PLATE_NO" : request.form.get("TRAFFIC_PLATE_NO") ,
                "AUTHORIZER_NAME" : request.form.get("AUTHORIZER_NAME") ,
                "AUTHORIZER_COUNTRY" : request.form.get("AUTHORIZER_COUNTRY") ,
                "AUTHORIZER_PASSPORT_NO" : request.form.get("AUTHORIZER_PASSPORT_NO") ,
                "AUTHORIZER_RESIDENT_EMIRATES_ID_NO" : request.form.get("AUTHORIZER_RESIDENT_EMIRATES_ID_NO") ,
                "TRAFFIC_PLATE_NO" : request.form.get("TRAFFIC_PLATE_NO") ,
                "VEHICLE_TYPE" : request.form.get("VEHICLE_TYPE") ,
                "VEHICLE_COLOR" : request.form.get("VEHICLE_COLOR") ,
                "VEHICLE_YEAR" : request.form.get("VEHICLE_YEAR") ,
                "ENGINE_NO" : request.form.get("ENGINE_NO") ,
                "CHASSIS_NO" : request.form.get("CHASSIS_NO") ,
                "OWNER_NAME" : request.form.get("OWNER_NAME") ,
                "OWNER_SIGN" : request.form.get("OWNER_SIGN") ,
                "ATTORNEY_NAME" : request.form.get("ATTORNEY_NAME") ,
                "ATTORNEY_SIGN" : request.form.get("ATTORNEY_SIGN") 
            }
            data = json.dumps(dict)   
            cursor = mysql.connection.cursor() 
            cursor.execute("SELECT * from form_entries where user_id=%s and form_id=%s;",[session['userid'],form_id])
            exist = cursor.fetchone()
            if exist:
                cursor.execute("DELETE from form_entries where id=%s",[exist['id']])            
                mysql.connection.commit()
            cursor.execute('INSERT into form_entries (form_id,user_id,data) VALUES (%s,%s,%s);',(form_id,session['userid'],data))
            mysql.connection.commit()

            

            # now hit api 
            data = {
                "country":country,
                  "name":name,
                  "passport":passport,
                  "id_no":id_no,
                  "plate_no":plate_no,
                  "emirate":emirate,
                  "name_2":name_2,
                  "country_2":country_2,
                  "passport_2":passport_2,
                  "id_no_2":id_no_2,
                  "vehicle_type":vehicle_type,
                  "color":color,
                  "year":year,
                  "engine_no":engine_no,
                  "chassis_no":chassis_no
            }
            response = requests.post("http://3.8.200.254/api/v1/power_of_attorney", json=data)

            if response.status_code == 200:
                filename = "power_of_attorney.pdf"
                with open(os.path.join(UPLOAD_FOLDER4,filename), "wb") as pdf_file:
                    pdf_file.write(response.content)
                    print("PDF saved successfully.")

                form_completed = True
                
                cursor.execute('INSERT into contract_pdfs (userid,formid,filename,date_time) VALUES (%s,%s,%s,%s);',(session['userid'],form_id,filename,date))
                mysql.connection.commit()
            else:
                print("Error with status code:", response.status_code)

            # --

        # log             
        pathfilename = None
        if form_completed:
            desc = session['name']+ " completed a form #"+str(form_id)
            file = "True"
            filename = filename
        else:
            desc = session['name']+ " updated a form #"+str(form_id)
            file = "False"
            filename = None
        cursor.execute('INSERT into contract_logs (userid,description,file,filename,date_time) VALUES (%s,%s,%s,%s,%s);',(session['userid'],desc,file,filename,date))
        mysql.connection.commit()

        return redirect(url_for("view_filled_contracts"))

    else:
        return redirect(url_for('login'))

@app.route("/view-filled-contracts")
def view_filled_contracts():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT form_id,user_id,data,forms.name as form_name, status from form_entries Inner Join forms on form_entries.form_id = forms.id where user_id=%s;',[session['userid']])
        forms = cursor.fetchall()
        user = {"id":session['userid'],"name":session['name'],"email":session['email'],"type":session['type'],"pic":session['pic']}
        return render_template("dashboard-view-filled-contracts.html",user=user,forms=forms)
    else:
        return redirect(url_for('login'))

@app.route("/download-filled-pdf/<int:form_id>")
def download_filled_pdf(form_id):
    if 'loggedin' in session:
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * from contract_pdfs where userid=%s and formid=%s;',[session['userid'],form_id])
        contract_pdf = cursor.fetchone()
        
        return send_file(os.path.join(UPLOAD_FOLDER4,contract_pdf['filename']), as_attachment=True)

        
    else:
        return redirect(url_for('login'))

@app.route("/scrap-pdf",methods=['GET','POST'])
def scrap_pdf():
        
    cursor = mysql.connection.cursor()
    if request.method == 'POST':    
        files = request.files.getlist("files[]")
        for i in files:
            date = datetime.datetime.now().strftime("%B %d, %Y")
            filename = secure_filename(i.filename)
            i.save(os.path.join(UPLOAD_FOLDER2,filename))
            cursor.execute('INSERT into pdf_files (userid,filename,size,date) VALUES (%s,%s,"not known yet",%s);',(session['userid'],filename,date))
            mysql.connection.commit()
            
            size = os.stat(os.path.join(UPLOAD_FOLDER2,filename)).st_size
            inserted_id = cursor.lastrowid
            cursor.execute('UPDATE pdf_files SET size=%s where id=%s',[size/1000,inserted_id])            
            mysql.connection.commit()
            
            # log 
            desc = session['name']+ " uploaded a pdf file."
            pathfilename = os.path.join(UPLOAD_FOLDER2,filename)
            file = "True"
            cursor.execute('INSERT into pdf_logs (userid,description,file,filename,date_time) VALUES (%s,%s,%s,%s,%s);',(session['userid'],desc,file,pathfilename,date))
            mysql.connection.commit()

        cursor.execute('SELECT * from pdf_files where userid=%s;',[session['userid']])
        data = cursor.fetchall()
        # filenames = []
        # for i in filename:
        #     filenames.append(i['filename'])
        return json.dumps(data)
    
    
    if 'loggedin' in session:
        cursor.execute('SELECT * from pdf_files where userid=%s;',[session['userid']])
        data = cursor.fetchall()
        user = {"id":session['userid'],"name":session['name'],"email":session['email'],"type":session['type'],"pic":session['pic']}
        return render_template("scrap-pdf.html",user=user,data=data)
    else:
        return redirect(url_for('login'))

@app.route("/view-scrapped-pdf")
def view_scrapped_pdf():
    if 'loggedin' in session:        
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * from api_pdfs where userid=%s;',[session['userid']])
        data = cursor.fetchall()
        user = {"id":session['userid'],"name":session['name'],"email":session['email'],"type":session['type'],"pic":session['pic']}
        return render_template("view-scrapped-pdf.html",user=user,data=data)
    else:
        return redirect(url_for('login'))

@app.route("/users")
def users():
    if 'loggedin' in session:        
        if session['type']=='admin':
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT * from users where type="user";')
            users = cursor.fetchall()
            user = {"id":session['userid'],"name":session['name'],"email":session['email'],"type":session['type'],"pic":session['pic']}
            return render_template("dashboard-users.html",user=user,users=users)
        else:
            return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))

@app.route("/pdf-logs")
def pdf_logs():
    if 'loggedin' in session:        
        if session['type']=='admin':
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT * from pdf_logs;')
            logs = cursor.fetchall()
            user = {"id":session['userid'],"name":session['name'],"email":session['email'],"type":session['type'],"pic":session['pic']}
            return render_template("dashboard-pdf-logs.html",user=user,logs=logs)
        else:
            return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))

@app.route("/contract-logs")
def contract_logs():
    if 'loggedin' in session:        
        if session['type']=='admin':
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT * from contract_logs;')
            logs = cursor.fetchall()
            user = {"id":session['userid'],"name":session['name'],"email":session['email'],"type":session['type'],"pic":session['pic']}
            return render_template("dashboard-contract-logs.html",user=user,logs=logs)
        else:
            return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))

@app.route("/remove-file/<int:file_id>")
def remove_file(file_id):
    if 'loggedin' in session: 
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * from pdf_files where id=%s;',[file_id])
        data = cursor.fetchone()
        if data['userid'] == int(session['userid']):
            cursor.execute('DELETE from pdf_files where id=%s',[file_id])
            mysql.connection.commit()
            try:
                os.remove(os.path.join(UPLOAD_FOLDER2,data['filename']))
            except:
                pass
            return redirect(url_for("scrap_pdf"))
        else:
            return redirect(url_for("scrap_pdf"))

    else:
        return redirect(url_for('login'))

@app.route("/delete-log/<string:type>/<int:id>")
def delete_log(type,id):
    cursor = mysql.connection.cursor()
    if 'loggedin' in session: 
        if type=="pdf":
            cursor.execute('DELETE from pdf_logs where id=%s',[id])
            mysql.connection.commit()
            return redirect(url_for("pdf_logs"))
        elif type=="contract":
            cursor.execute('DELETE from contract_logs where id=%s',[id])
            mysql.connection.commit()
            return redirect(url_for("contract_logs"))

    else:
        return redirect(url_for('login'))


@app.route("/download-log-file/<int:id>")
def download_log_file(id):
    cursor = mysql.connection.cursor()
    if 'loggedin' in session: 
        cursor.execute('Select * from pdf_logs where id=%s',[id])
        data = cursor.fetchone()       
        return send_file(data['filename'], as_attachment=True)

    else:
        return redirect(url_for('login'))

@app.route("/download-contract-log-file/<int:id>")
def download_contract_log_file(id):
    cursor = mysql.connection.cursor()
    if 'loggedin' in session: 
        cursor.execute('Select * from contract_logs where id=%s',[id])
        data = cursor.fetchone()       
        return send_file(os.path.join(UPLOAD_FOLDER4,data['filename']), as_attachment=True)

    else:
        return redirect(url_for('login'))


@app.route("/remove-processed-file/<int:file_id>")
def remove_processed_file(file_id):
    if 'loggedin' in session: 
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * from api_pdfs where id=%s;',[file_id])
        data = cursor.fetchone()
        if data['userid'] == int(session['userid']):
            cursor.execute('DELETE from api_pdfs where id=%s',[file_id])
            mysql.connection.commit()
            try:
                os.remove(os.path.join(UPLOAD_FOLDER3,data['output']))
            except:
                pass
            return redirect(url_for("view_scrapped_pdf"))
        else:
            return redirect(url_for("view_scrapped_pdf"))

    else:
        return redirect(url_for('login'))

@app.route("/download-processed-file/<int:file_id>")
def download_file(file_id):
    if 'loggedin' in session: 
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * from api_pdfs where id=%s;',[file_id])
        data = cursor.fetchone()        
        if data['userid'] == int(session['userid']):
            try:
                return send_file(os.path.join(UPLOAD_FOLDER3,data['output']), as_attachment=True)
            except Exception as e:
                return str(e)
        else:
            return redirect(url_for("view_scrapped_pdf"))

    else:
        return redirect(url_for('login'))


@app.route("/process-files",methods=['POST'])
def process_files():
    if 'loggedin' in session: 
        filenames = []
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * from pdf_files where userid=%s;',[session['userid']])
        data = cursor.fetchall()
        if not data:
            return "No data"
    
        date = datetime.datetime.now().strftime("%B %d, %Y")
        for i in data:
            filenames.append(i['filename'])
            # api work 
        url = "http://137.184.226.162/api/v1/send_file"
        for file in filenames:
            file_path = os.path.join(UPLOAD_FOLDER2,file)
            with open(file_path, "rb") as f:
                file_data = f.read()
            files = {"file": (file, file_data)}
            data = {"show_contacts": 1}
            response = requests.post(url, data=data, files=files)
            if response.status_code == 200:
                filename = file.replace(".pdf","")
                filename = filename+"_output.pdf"
                with open(os.path.join(UPLOAD_FOLDER3,filename), "wb") as f:
                    f.write(response.content)
                cursor.execute('INSERT into api_pdfs (userid,input,output,date) VALUES (%s,%s,%s,%s);',(session['userid'],file,filename,date))
                mysql.connection.commit()
                # log 
                desc = session['name']+ " processed a pdf file."
                pathfilename = os.path.join(UPLOAD_FOLDER3,filename)
                file = "True" 
                cursor.execute('INSERT into pdf_logs (userid,description,file,filename,date_time) VALUES (%s,%s,%s,%s,%s);',(session['userid'],desc,file,pathfilename,date))
                mysql.connection.commit()

                print("PDF saved successfully")
            else:
                print("Error generating PDF")
        return "completed"
    else:
        return redirect(url_for('login'))


@app.route("/test")
def test():
    filenames = []
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * from pdf_files where userid=%s;',[session['userid']])
    data = cursor.fetchall()
    
    date = datetime.datetime.now().strftime("%B %d, %Y")
    for i in data:
        filenames.append(i['filename'])
        # api work 
    url = "http://137.184.226.162/api/v1/send_file"
    for file in filenames:
        file_path = os.path.join(UPLOAD_FOLDER2,file)
        with open(file_path, "rb") as f:
            file_data = f.read()
        files = {"file": (file, file_data)}
        data = {"show_contacts": 1}
        response = requests.post(url, data=data, files=files)
        if response.status_code == 200:
            filename = file.replace(".pdf","")
            filename = filename+"_output.pdf"
            with open(os.path.join(UPLOAD_FOLDER3,filename), "wb") as f:
                f.write(response.content)
            cursor.execute('INSERT into api_pdfs (userid,input,output,date) VALUES (%s,%s,%s,%s);',(session['userid'],file,filename,date))
            mysql.connection.commit()
            print("PDF saved successfully")
        else:
            print("Error generating PDF")

    
    return jsonify({"data":data})

@app.route("/account-status/<string:type>/<int:id>")
def disable_user_account(type,id):
    if 'loggedin' in session:        
        if session['type']=='admin':
            cursor = mysql.connection.cursor()
            if type == "active":
                cursor.execute('UPDATE USERS SET status="active" where id=%s;',[id])
            elif type == "inactive":
                cursor.execute('UPDATE USERS SET status="inactive" where id=%s;',[id])
            mysql.connection.commit()
            return redirect(url_for("users"))
        else:
            return redirect(url_for("dashboard"))
    else:
        return redirect(url_for("dashboard"))

                





# ------------------- DASHBOARD ----------------------

if __name__ == '__main__':
    app.run(debug=True)