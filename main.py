from __future__ import with_statement
from contextlib import closing
# all the imports
import sqlite3
import datetime
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
     
from functools import wraps


# configuration
'''with sqlite3 commend installed: sqlite3 /tmp/flaskr.db < schema.sql'''
DATABASE = '/tmp/flaskr.db'
DEBUG = True
CSRF_ENABLED = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'


# create our little application :)
''' __name__ is this file'''
app = Flask(__name__)
app.config.from_object(__name__)

app.config.from_envvar('FLASKR_SETTINGS', silent=True)

''' if sqlite3 command is not installed, this will also work, 
then in shell:
>>> from [file] import init_db
>>> init_db()
'''
def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    g.db.close()
    
def login_required(test):
    @wraps(test)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return test(*args, **kwargs)
        else:
            flash('You need to login')
            return redirect(url_for('login'))
    return wrap

class MissingParamException(Exception):
    def __init__(self):
        print "form fields empty"
    
''' SESSIONS '''
@app.route('/login', methods=['GET', 'POST'])
def login():
    error=None
    if request.method=='POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in']=True
            flash('You were logged in')
            return redirect(url_for('show_logs'))
    return render_template('login.html', error=error)
    
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_logs'))

'''LOGS'''    

@app.route('/')
def show_logs():
    ''' include date later'''
    addTrue = False
    if 'date' in request.args:
        date = datetime.datetime.strptime(request.args['date'], "%Y-%m-%d").date()
    else:
        date = datetime.date.today()
    
    if date == datetime.date.today():
        addTrue = True
        
    if date == datetime.date.today() - datetime.timedelta(days=1):
        addTrue = True
    
    yesterday = date - datetime.timedelta(days=1)
    tomorrow = date + datetime.timedelta(days=1)
    day = date.strftime("%A, %B %e, %G")
    l = g.db.execute("SELECT * FROM logs WHERE date='%s' ORDER BY id desc" % date)
    a = g.db.execute("SELECT DISTINCT id, name FROM activities")
    ''' dict factory replacement?'''
    logs = [dict(id=row[0], activity_id=row[1], date=row[2], time=row[3]) for row in l.fetchall()]
    activities = [dict(id=row[0], name=row[1]) for row in a.fetchall()]
    return render_template('show_logs.html', logs=logs, activities=activities, day=day, addTrue=addTrue, yesterday=str(yesterday), tomorrow=str(tomorrow))

@app.route('/addLogs', methods=['POST'])
@login_required
def add_log():
    try:
        time = request.form['time']
        if time==None or time=='':
            raise MissingParamException
        g.db.execute('INSERT INTO logs (activity_id, date, time) VALUES (?, ?, ?)', [request.form['activity'], str(datetime.date.today()), time])
        g.db.commit()
        flash('New entry was successfully posted!')
        return redirect(url_for('show_logs'))
    except MissingParamException:
        flash('All fields must be filled.')
        return redirect(url_for('show_logs'))

'''ACTIVITIES'''
@app.route('/activities')
def show_activities():
    a = g.db.execute("SELECT DISTINCT id, name FROM activities")
    activities = [dict(id=row[0], name=row[1]) for row in a.fetchall()]
    return render_template('show_activities.html', activities=activities)

@app.route('/addActivities', methods=['POST'])
@login_required
def add_activity():
    try:
        name = request.form['name']
        if name==None or name=='':
            raise MissingParamException
        g.db.execute('INSERT INTO activities (name, difficulty, sessions) VALUES (?, ?, ?)', [name, request.form['difficulty'], request.form['sessions']])
        g.db.commit()
        flash('New entry was successfully posted!')
        return redirect(url_for('show_activities'))
    except MissingParamException:
        flash('All fields must be filled')
        return redirect(url_for('show_activities'))

'''HELPERS'''
def get_activity_name(id):
    n = g.db.execute('SELECT name FROM activities WHERE id=%s' %id)
    a = [dict(name=row[0]) for row in n.fetchall()]
    return a[0]['name']
    
def get_activity_sessions(id):
    s = g.db.execute('SELECT sessions FROM activities WHERE id=%s' %id)
    a = [dict(sessions=row[0]) for row in s.fetchall()]
    return a[0]['sessions']

app.jinja_env.globals.update(get_activity_name=get_activity_name)
app.jinja_env.globals.update(get_activity_sessions=get_activity_sessions)

if __name__ == '__main__':
    app.run()