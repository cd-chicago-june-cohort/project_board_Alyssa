from flask import Flask, session, request, redirect, render_template, flash
from mysqlconnection import MySQLConnector
import re
import md5
import datetime

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')

app = Flask(__name__)
app.secret_key = '04c46b3b62477fc999e63d62c635d97c'
mysql = MySQLConnector(app, 'project_board')

# Initial login and registration page
@app.route('/')
def index():
    return render_template('index.html')

# Login authentication and processing
@app.route('/authenticate', methods = ["POST"])
def authenticate():
    email = request.form['email']
    password = md5.new(request.form['password']).hexdigest()
    data = {
        'email': email,
        'password': password
    }
    errors=True
    query = 'select * from users where email = :email'
    db_check = mysql.query_db(query, data)
    # Validations and error messages
    if not EMAIL_REGEX.match(email):
        flash("Invalid Email Address!")
    elif len(db_check) != 1:
        flash("E-mail address not registered.  Please register an account")
    elif len(email) < 1 or len(request.form['password']) < 1:
        flash("All fields are required!")
    elif db_check[0]['password'] != password:
        flash('Incorrect password, please try again')
    else:
        errors=False
    # no errors, set session id, login and go to the wall
    if errors:
        return redirect('/')
    else:
        session['id'] = db_check[0]['id']
        return redirect ('/dashboard')

# Registration validation and processing
@app.route('/register', methods = ["POST"])
def register():
    today = datetime.date.today()
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']
    date_of_birth = request.form['date_of_birth']
    password = request.form['password']
    pw_confirm = request.form['pw_confirm']
    # Error for any blank fields (before processing any data)
    if len(first_name) < 1 or len(last_name) < 1 or len(email) < 1 or len(date_of_birth) < 1 or len(password) < 1 or len(pw_confirm) < 1:
        flash("All fields are required!")
        return redirect('/')
    # Process date of birth and password into the formats needed for storage
    dob = datetime.datetime.strptime(date_of_birth, "%Y-%m-%d").date()
    hashed_password = md5.new(request.form['password']).hexdigest()
    data = {
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
        'date_of_birth': dob,
        'password': hashed_password
    }
    errors=True
    query = 'select * from users where email = :email'
    db_check = mysql.query_db(query, data)
    # Check to see if user is already in database
    if len(db_check) == 1:
        flash("This e-mail address is already registered.  Please try logging in, or register with a different e-mail address")
    # Validations and error messages
    elif not EMAIL_REGEX.match(email):
        flash("Invalid Email Address!")
    elif dob > today:
        flash("Birthday must be in the past")
    elif len(password) < 8:
        flash("Password must be at least 8 characters")
    elif password != pw_confirm:
        flash("Passwords do not match")
    else:
        errors=False
    # if not in database AND no errors, update database, set session id and go to the dashboard, else reload registration page with flash message showing first error
    if errors:
        return redirect('/')
    else:
        insert = 'insert into users (first_name, last_name, email, date_of_birth, password, created_at) values(:first_name, :last_name, :email, :date_of_birth, :password, NOW())'
        session['id'] = mysql.query_db(insert, data)
        return redirect ('/dashboard')


# Display current users projects
@app.route('/dashboard')
def dashboard():
    query = 'select projects.name, date_due, date_format(date_completed,"%Y-%m-%d") as date_completed, projects.id, status from projects join users on user_id = users.id where user_id = :user_id'
    data = {'user_id' : session['id']}
    user_projects = mysql.query_db(query, data)
    return render_template('dashboard.html', user_projects = user_projects)

# Display project details
@app.route('/show/<project_id>')
def show(project_id):
    query = 'select name, description, date_due, status, date_completed from projects where id = :project_id'
    data = {'project_id': project_id}
    project_info = mysql.query_db(query, data)
    project = project_info[0]
    return render_template ('show.html', project=project)

# Display form to add a project and update project table
@app.route('/add', methods = ["GET", "POST"])
def add():
    if request.method == 'POST':  
        name = request.form['name']
        deadline = request.form['deadline']
        date_due = datetime.datetime.strptime(deadline, "%Y-%m-%d").date()
        description = request.form['description']
        status = request.form['status']
        user_id = session['id']
        insert = "insert into projects (name, date_due, description, status, user_id) values (:name, :date_due, :description, :status, :user_id)" 
        data = {
            'name': name,
            'date_due': date_due,
            'description': description,
            'status': status,
            'user_id': session['id']
        }
        mysql.query_db(insert, data)
        return redirect('/dashboard')
    else:
        return render_template('add.html')

# Delete a project
@app.route('/destroy/<project_id>')
def destroy(project_id):
    delete = 'delete from projects where id = :id'
    data = {'id': project_id}
    mysql.query_db(delete, data)
    return redirect('/dashboard')

# Mark a project as completed
@app.route('/complete/<project_id>')
def complete(project_id):
    date_completed = datetime.date.today()
    update = 'update projects set date_completed = :date_completed, status = :status where id = :id'
    data = {
        'date_completed': date_completed,
        'id': project_id,
        'status': 'complete',  
    }
    mysql.query_db(update, data)
    return redirect('/dashboard')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')
app.run(debug=True)