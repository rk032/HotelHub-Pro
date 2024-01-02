from flask import Flask, render_template, make_response, flash, redirect, url_for, session, request, logging
import random
from flask_mysqldb import MySQL
from flask_wtf import Form
from wtforms import DateField
from functools import wraps
import pdfkit
import os
app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Harish1234'
app.config['MYSQL_DB'] = 'hotel_management'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init MYSQL
mysql = MySQL(app)

# Index
@app.route('/')
def index():
    return render_template('home.html')

@app.route('/about')
def about():
	return render_template('about.html')

@app.route('/amenities')
def amenities():

    cur = mysql.connection.cursor()
    cur.callproc('get_all_amenities')
    amenities = cur.fetchall()
    if len(amenities) > 0:
        return render_template('amenities.html', amenities=amenities)
    else:
        msg = 'No facilites available currently'
        return render_template('amenities.html', msg=msg)

@app.route('/rooms')
def rooms():
    cur = mysql.connection.cursor()
    result=cur.callproc('get_all_rooms')
    rooms = cur.fetchall() 
    print(rooms)   
    for r in rooms:
        if r['r_type']==1 and r['r_capacity']==1:
            r['price']=1000
        elif r['r_type']==1 and r['r_capacity']==2:
            r['price']=2000
        elif r['r_type']==1 and r['r_capacity']==3:
            r['price']=3000
        elif r['r_type']==2 and r['r_capacity']==1:
            r['price']=2500
        elif r['r_type']==2 and r['r_capacity']==2:
            r['price']=3500
        elif r['r_type']==2 and r['r_capacity']==3:
            r['price']=4500
        elif r['r_type']==3 and r['r_capacity']==1:
            r['price']=5000
        elif r['r_type']==3 and r['r_capacity']==2:
            r['price']=6000
        elif r['r_type']==3 and r['r_capacity']==3:
            r['price']=7000
    if len(rooms) > 0:
        return render_template('rooms.html', rooms=rooms)
    else:
        return render_template('rooms.html', msg='No rooms available currently')

@app.route('/view_amenity/<string:id>/')
def view_amenity(id):
    cur = mysql.connection.cursor()
    cur.callproc('get_amenity_by_id', [id])
    amenity = cur.fetchone()
    print(amenity)
    return render_template('view_amenity.html', amenity=amenity)

# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        # Create cursor
        cur = mysql.connection.cursor()
        cur.callproc('insert_admin', [name, email, username, password])
        mysql.connection.commit()
        cur.close()
        flash('You are now registered and can log in', 'success')
        return redirect(url_for('login'))
    else:
        return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        # Create cursor
        cur = mysql.connection.cursor()
        # Get user by username
        result = cur.execute("SELECT * FROM admins WHERE username = %s", [username])
        if result > 0:
            data = cur.fetchone()
            password = data['password']
            # Compare Passwords
            if (request.form['password'] == password):
                print("matched and redirecting....")
                session['logged_in'] = True
                session['username']  = username
                flash('Successfully logged in!', 'success')
                return redirect(url_for('dashboard'))
            else:
                print("wrong password")
                error = 'Invalid login'
                app.logger.info('PASSWORD DOES NOT MATCH')
                return render_template('login.html', error=error)
        else:
            error = 'Username not found'
            app.logger.info('NO SUCH USER')
            return render_template('login.html', error=error)
    else:
        return render_template('login.html')


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return (f(*args, **kwargs))
        else:
            flash('Unauthorised access!', 'danger')
            return redirect(url_for('login'))
    return wrap

@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@is_logged_in
def dashboard():
    return render_template('dashboard.html')

@app.route('/admin_amenities')
@is_logged_in
def admin_amenities():
    cur = mysql.connection.cursor()
    result = cur.callproc('get_all_amenities')
    amenities = cur.fetchall()
    if len(amenities) >= 0:
        return render_template('admin_amenities.html', amenities=amenities)
    else:
        return render_template('dashboard.html')
    

@app.route('/add_amenity', methods=['GET', 'POST'])
@is_logged_in
def add_amenity():
    import mysql.connector
    db_config = {
    'user': 'root',
    'password': 'Harish1234',
    'host': 'localhost',
    'database': 'hotel_management',
    'raise_on_warnings': True
    }

    if request.method=="POST":
        idd = request.form['id']
        type = request.form['type']
        status = request.form['status']
        capacity = request.form['capacity']
        title = request.form['title']
        description = request.form['description']
        try:
            cnx = mysql.connector.connect(**db_config)
            cur= cnx.cursor()
            cur.callproc('add_amenity', (idd, type, status, capacity, title, description))
            cnx.commit()
            flash('Facility Added Successfully', 'success')
            return redirect(url_for('admin_amenities'))
        except mysql.connector.Error as err:
            if err.errno == mysql.connector.errorcode.ER_SIGNAL_EXCEPTION:
                flash('Error: Amenity ID already exists', 'danger')
                return redirect(url_for('admin_amenities'))
            else:
                flash(f"Error: {err}", 'danger')
                return redirect(url_for('admin_amenities'))
        finally:
            if 'cnx' in locals() and cnx.is_connected():
                cnx.close()
                return redirect(url_for('admin_amenities'))
    else:
        return render_template('add_amenity.html')


@app.route('/edit_amenity/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_amenity(id):
    if request.method == "POST":
        type = request.form['type']
        status = request.form['status']
        capacity = request.form['capacity']
        title = request.form['title']
        description = request.form['description']

        cur = mysql.connection.cursor()
        cur.callproc('update_amenity', (id, type, status, capacity, title, description))
        mysql.connection.commit()
        cur.close()

        flash('Facility Updated successfully', 'success')
        return redirect(url_for('dashboard'))
    else:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM amenities WHERE a_id = %s", [id])
        data = cur.fetchone()
        cur.close()

        return render_template('edit_amenity.html', amenity=data)


@app.route('/delete_amenity/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def delete_amenity(id):
    cur = mysql.connection.cursor()
    cur.callproc('delete_amenity', [id])
    mysql.connection.commit()
    cur.close()
    flash('Facility Deleted', 'success')
    return redirect(url_for('admin_amenities'))

@app.route('/admin_rooms')
@is_logged_in
def admin_rooms():
    cur = mysql.connection.cursor()
    result = cur.callproc('get_all_rooms')
    rooms = cur.fetchall()
    if len(rooms) > 0:
        return render_template('admin_rooms.html', rooms=rooms)
    else:
        flash('No Rooms available!', 'danger')
        redirect(url_for('add_room'))
    cur.close()
    return render_template('admin_rooms.html')

@app.route('/add_room', methods=['GET', 'POST'])
@is_logged_in
def add_room():
    import mysql.connector
    db_config = {
    'user': 'root',
    'password': 'Harish1234',
    'host': 'localhost',
    'database': 'hotel_management',
    'raise_on_warnings': True
    }

    if request.method == 'POST':
        id = request.form['id']
        number = request.form['number']
        type = request.form['type']
        status = request.form['status']
        capacity = request.form['capacity']
        try:
            cnx = mysql.connector.connect(**db_config)
            cursor = cnx.cursor()
            cursor.callproc('insert_room', [id, number, type, capacity, status])
            cnx.commit()
            cursor.close()
            flash('Room added successfully!', 'success')
            return redirect(url_for('admin_rooms'))
        except mysql.connector.Error as err:
            if err.errno == mysql.connector.errorcode.ER_SIGNAL_EXCEPTION:
                flash('Error: Room ID already exists', 'danger')
                return redirect(url_for('admin_rooms'))
            else:
                flash(f"Error: {err}", 'danger')
                return redirect(url_for('admin_rooms'))
        finally:
            if 'cnx' in locals() and cnx.is_connected():
                cnx.close()
                return redirect(url_for('admin_rooms'))
    else:
        return render_template('add_room.html')


@app.route('/edit_room/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_room(id):
    if request.method == 'POST':
        type = request.form['type']
        status = request.form['status']
        capacity = request.form['capacity']
        cur = mysql.connection.cursor()
        cur.callproc('update_room', (id, type, status, capacity))
        mysql.connection.commit()
        cur.close()
        flash('Room Updated successfully', 'success')
        return redirect(url_for('admin_rooms'))
    else:
        return render_template('edit_room.html', id=id)

@app.route('/delete_room/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def delete_room(id):
    cur=mysql.connection.cursor()
    cur.callproc('delete_room', (id,))
    mysql.connection.commit()
    cur.close()
    flash('Room Deleted', 'success')
    return redirect(url_for('admin_rooms'))

@app.route('/bookings/<string:id>', methods=['GET', 'POST'])
def bookings(id):
    global g_id, b_id
    b_id = random.randint(1001, 10000)

    cur = mysql.connection.cursor()
    
    if id[0] == 'R':
        result = cur.execute("SELECT * FROM rooms WHERE r_id=%s", [id])
    else:
        result = cur.execute("SELECT * FROM amenities WHERE a_id=%s", [id])
    
    amenity = cur.fetchone()

    if id[0] == 'R' and amenity['r_status'] == 1:
        return redirect(url_for('rooms'))

    if id[0] != 'R' and amenity['a_status'] == 1:
        return redirect(url_for('amenities'))

    f_type=0
    f_cost=0
    if request.method == 'POST':
        check_in = request.form['check_in']
        check_out = request.form['check_out']
        print(check_in)
        print(check_out)
        if id[0] == 'R':
            g_id = random.randint(1, 1000)

            result = cur.execute("SELECT r_type FROM rooms WHERE r_id=%s",[id])
            result = cur.fetchone()
            f_type = result['r_type']
            print(f_type)
            result = cur.execute("SELECT cost FROM charges WHERE code = 1 AND type=%s",[f_type])
            result = cur.fetchone()
            f_cost = result['cost']

            print(f_type, f_cost)
        else:
            g_id =request.form['g_id']
            
            result = cur.execute("SELECT a_type FROM amenities WHERE a_id=%s",[id])
            result = cur.fetchone()
            f_type = result['a_type']

            result = cur.execute("SELECT cost FROM charges WHERE code = 0 AND type=%s",[f_type])
            result = cur.fetchone()
            f_cost = result['cost']

            print(f_type, f_cost)
            
            check_out = check_in

        status = 1
        name = request.form['name']
       
        count = request.form['count']
        email = request.form['email']
        streetno = request.form['streetno']
        city = request.form['city']
        state = request.form['state']   
        country =request.form['country']
        pincode = request.form['pincode']
        if (not name.isalpha()) and (len(pincode)!=6):
            return render_template('bookings.html')
        print(name,count,email)
        if id[0] == 'R':
            cur.execute("INSERT INTO bookings(b_id, r_id, g_id, b_status, a_id, st, et, f_type, f_cost) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)", (b_id, id, g_id, status, '0', check_in, check_out, f_type, f_cost))
            cur.execute("INSERT INTO guests(g_id, g_name, g_email, g_count, g_streetno, g_city, g_state, g_country, g_pincode) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)",(g_id, name, email, count, streetno, city, state, country, pincode))
            cur.execute("UPDATE rooms set r_status=1 where r_id=%s",[id])
        else:
            cur.execute("INSERT INTO bookings(b_id, r_id, g_id, b_status, a_id, st, et, f_type, f_cost) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)", (b_id, '0', g_id, status, id, check_in, check_out, f_type, f_cost))
            cur.execute("UPDATE amenities set a_status=1 where a_id=%s",[id])
        
        mysql.connection.commit()

        cur.close()

        flash('Successfully Booked!', 'success')
        return redirect(url_for('bookings', id=id))

    return render_template('bookings.html', amenity=amenity, id=id)  

@app.route('/admin_guests')
def admin_guests():
    cur = mysql.connection.cursor()

    cur.callproc('select_all_guests')
    guests = cur.fetchall()

    if guests:
        return render_template('guests.html', guests=guests)
    else:
        msg = 'No guests in the Hotel currently'
        return render_template('guests.html', msg=msg)

@app.route('/generate_bill/<string:id>')
def generate_bill(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM bookings WHERE  g_id = %s", [id])
    bookings = cur.fetchone()
    cur.execute("SELECT * FROM guests WHERE g_id = %s", [id])
    guest = cur.fetchone()
    delta = bookings['et']-bookings['st']
    total = bookings['f_cost']
    total*=delta.days
    pathToWkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    config = pdfkit.configuration(wkhtmltopdf=pathToWkhtmltopdf)
    rendered = render_template('generate_bill.html', len=len(bookings), guest=guest, bookings=bookings, total=total)
    pdf = pdfkit.from_string(rendered, False,configuration=config,options={"enable-local-file-access": ""})
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=Bill.pdf'
    cur.execute("DELETE FROM guests WHERE g_id = %s ",[id])
    mysql.connection.commit()

    return response

@app.route('/billings', methods=['GET', 'POST'])
def billings():

    if request.method == 'POST':
        id = request.form['g_id']
        print(id)
        return redirect(url_for('generate_bill', id=id))
    else:
        return render_template('billings.html')

if __name__ == '__main__':
    SECRET_KEY = os.urandom(32)
    app.config['SECRET_KEY'] = SECRET_KEY

    SECRET_KEY = os.urandom(32)
    app.config['WTF_CSRF_SECRET_KEY']=SECRET_KEY

    app.run(debug = True)
