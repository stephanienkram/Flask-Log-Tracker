from __future__ import with_statement
from contextlib import closing
# all the imports
import sqlite3
import datetime
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
     
from functools import wraps


# configuration
'''with sqlite3 commend installed: sqlite3 logger.db < schema.sql'''
DATABASE = 'logger.db'
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
def dict_factory(cursor, row):
    d = {}
    for idx,col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def connect_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = dict_factory
    return conn

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
    addTrue = False
    today = False
    if 'date' in request.args:
        date = datetime.datetime.strptime(request.args['date'], "%Y-%m-%d").date()
    else:
        date = datetime.date.today()
    
    if date == datetime.date.today():
        addTrue = True
        today = True
    if date == datetime.date.today() - datetime.timedelta(days=1):
        addTrue = True
    
    yesterday = date - datetime.timedelta(days=1)
    tomorrow = date + datetime.timedelta(days=1)
    day = date.strftime("%A, %B %e, %G")
    logs = g.db.execute("SELECT * FROM logs WHERE date='%s' ORDER BY id desc" % date)
    skills = g.db.execute("SELECT DISTINCT id, name FROM skills")
    
    user = getUser()

    return render_template('logs/show_logs.html', users=user, logs=logs, skills=skills, day=day, addTrue=addTrue, today=today, yesterday=str(yesterday), tomorrow=str(tomorrow))

@app.route('/addLogs', methods=['POST'])
@login_required
def add_log():
    try:
        app.logger.info("Add log check: %s" % request.form)
        time = request.form['time']
        if time=='' or request.form['activity']=='':
            raise MissingParamException
        ''' calculate experience points!'''
        activities = g.db.execute('SELECT * FROM activities WHERE id = %s' % request.form['activity'])
        a = activities.fetchone()
        if a['sessions'] == 'm':
            exp = a['difficulty'] * int(time)
        else:
            exp = a['difficulty']
        
        users = g.db.execute("SELECT * FROM users WHERE id=%s" % 1)
        user = users.fetchone()
        user['exp'] += exp
        g.db.execute("UPDATE users SET exp=? WHERE id=?", (user['exp'], user['id']))
        g.db.commit()
        checkLevelUp()
        g.db.execute('INSERT INTO logs (activity_id, date, time, exp) VALUES (?, ?, ?, ?)', [request.form['activity'], str(datetime.date.today()), time, exp])
        g.db.commit()
        flash('New entry was successfully posted!')
        return redirect(url_for('show_logs'))
    except MissingParamException:
        flash('All fields must be filled.')
        return redirect(url_for('show_logs'))
    
@app.route('/delete_log/<l_id>', methods=["POST"])
def delete_log(l_id):
    g.db.execute("DELETE FROM logs WHERE id=%s" % l_id)
    g.db.commit()
    app.logger.info("Log %s deleted from db" % l_id)
    flash('Log deleted')
    return redirect(url_for('show_logs'))
    
    






'''ACTIVITIES'''
@app.route('/activities')
def show_activities():
    a = g.db.execute("SELECT * FROM activities WHERE active=1")
    activities = a.fetchall()
    s = g.db.execute("SELECT * FROM skills WHERE active=1")
    skills = s.fetchall()
    
    user = getUser()
    
    return render_template('activities/show_activities.html', users=user, activities=activities, skills=skills)

@app.route('/activity/<a_id>')
def show_a(a_id=None):
    ''' list all current logs'''
    if a_id==None:
        redirect(url_for('activities'))
    activities = g.db.execute("SELECT id, name, skill_id FROM activities WHERE id = %s AND active=1" % a_id)
    a = activities.fetchone()
    app.logger.info("Showing activity: %s" % a)
    skills = g.db.execute("SELECT * FROM skills WHERE id=%s AND active=1" % a['skill_id'])
    s = skills.fetchone()
    logs = g.db.execute("SELECT * FROM logs WHERE activity_id=%s" % a['id'])
    l = logs.fetchall()
    
    user = getUser()
    
    return render_template('activities/show.html', users=user, activity=a, skill=s, logs=l)

@app.route('/addActivities', methods=['POST'])
@login_required
def add_activity():
    try:
        app.logger.info("Add activity check: %s" % request.form)
        name = request.form['name']
        difficulty = request.form['difficulty']
        skill = request.form['skill']
        sessions = request.form['sessions']
        if name=='':
            app.logger.info("Exception raised: no name")
            raise MissingParamException
        if difficulty=='':
            app.logger.info("Exception raised: no difficulty")
            raise MissingParamException 
        if skill=='':
            app.logger.info("Exception raised: no skill")
            raise MissingParamException
        if sessions=='':
            app.logger.info("Exception raised: no sessions")
            raise MissingParamException
        check = g.db.execute("SELECT name FROM activities WHERE name='%s'" % name.lower())
        if check.fetchone() is not None:
            flash('That activity already exists')
            return redirect(url_for('show_activities'))
        g.db.execute('INSERT INTO activities (name, skill_id, difficulty, sessions, active) VALUES (?, ?, ?, ?, ?)', [name.lower(), request.form['skill'], request.form['difficulty'], request.form['sessions'], 1])
        g.db.commit()
        flash('New activity was successfully added!')
        return redirect(url_for('show_activities'))
    except MissingParamException:
        flash('All fields must be filled')
        return redirect(url_for('show_activities'))
    
@app.route('/delete_activity/<a_id>', methods=['POST'])
@login_required
def delete_activity(a_id):
    ''' deactivates so that logs still work correctly'''
    g.db.execute("UPDATE activities SET active=0 WHERE id=%s and active=1"% a_id)
    g.db.commit()
    app.logger.info("Activity %s deactivated" % a_id)
    flash("Activity deleted")
    return redirect(url_for('show_activities'))
    
    
    
    
    
''' SKILLS '''
@app.route('/skills')
def show_skills():
    s = g.db.execute("SELECT * FROM skills WHERE active=1")
    skills = s.fetchall()
    
    user = getUser()
    
    return render_template('skills/show_skills.html', users=user, skills=skills)

@app.route('/skill/<s_id>')
def show_s(s_id=None):
    ''' list all activities '''
    if s_id==None:
        redirect(url_for('skills'))
    skills = g.db.execute("SELECT id, name FROM skills WHERE id = %s AND active=1" % s_id)
    s = skills.fetchone()
    activities = g.db.execute("SELECT * FROM activities WHERE skill_id = %s AND active=1" % s['id'])
    
    user = getUser()
    
    return render_template('skills/show.html', users=user, skill=s, activities=activities.fetchall())

@app.route('/addSkills', methods=['POST'])
@login_required
def add_skill():
    try:
        name = request.form['name']
        if name==None or name=='':
            raise MissingParamException
        ''' check and see if skill is already in the db'''
        check = g.db.execute("SELECT name FROM skills WHERE name='%s' AND active=1" % name.lower())
        if check.fetchone() is not None:
            
            ''' active existing skill maybe? '''
            flash('That skill already exists')
            return redirect(url_for('show_skills'))
        g.db.execute('INSERT INTO skills (name, user_id, active) VALUES (?, ?, ?)', [name.lower(), 0, 1])
        g.db.commit()
        flash('New skill successfully added!')
        return redirect(url_for('show_skills'))
    except MissingParamException:
        flash('All fields must be filled')
        return redirect(url_for('show_skills'))
    
@app.route('/delete_skill/<s_id>', methods=['POST'])
@login_required
def delete_skill(s_id):
    ''' actually deactivates it, so that activities/logs will stay visually correct'''
    ''' check if there are no activities linked to it'''
    a = g.db.execute("SELECT * FROM activities WHERE skill_id = %s and active=1" % s_id)
    activities = a.fetchall()
    if len(activities) > 0:
        app.logger.info("Delete skill %s failed: skill still has active activities" % s_id)
        flash("Can't delete skills that still have activities")
        return redirect(url_for('show_skills'))
    g.db.execute("UPDATE skills SET active=0 WHERE id=%s" % s_id)
    g.db.commit()
    app.logger.info("Skill %s deactivated" % s_id)
    flash("Skill deleted")
    return redirect(url_for('show_skills'))






'''HELPERS'''
def getUser():
    users = g.db.execute("SELECT * FROM users WHERE id=%s" % 1)
    user = users.fetchone()
    app.logger.info(user)
    if user is None:
        g.db.execute("INSERT INTO users (id, name, password, level, exp) VALUES (1, 'admin', 'password', 1, 0)")
        g.db.commit()
        users = g.db.execute("SELECT * FROM users WHERE id=%s" % 1)
        user = users.fetchone()
        app.logger.info(user)
    return user    

def checkLevelUp():
    users = g.db.execute("SELECT * FROM users WHERE id=%s" % 1)
    user = users.fetchone()
    level = user['level']
    app.logger.info("Checking if level %s user levels up" % level)
    ''' create level guide'''
    total = 100
    diff = 0
    import math
    l = [0, 0, 100]
    for i in range(100):
        diff = round(125 + math.pow(2.0, (i/2.0)))
        total += diff
        l.append(total)
    
    app.logger.info("Current exp: %s, Exp req for level up: %s" % (user['exp'], l[level+1]))
        
    if user['exp'] > l[level+1]:
        user['level'] += 1
        app.logger.info('Level up! Move from levels %s => %s' % (level, level+1))
        
    g.db.execute("UPDATE users SET level=? WHERE id=?", (user['level'], user['id']))
    g.db.commit()
        
    
def get_activity_name(a_id):
    a = g.db.execute('SELECT name FROM activities WHERE id=%s' %a_id)
    return a.fetchone()['name']
    
def get_activity_sessions(a_id):
    a = g.db.execute('SELECT sessions FROM activities WHERE id=%s' %a_id)
    return a.fetchone()['sessions']

def get_skill_name(a_id):
    a = g.db.execute('SELECT skill_id FROM activities WHERE id=%s' %a_id)
    skill_id = a.fetchone()['skill_id']
    s = g.db.execute('SELECT name FROM skills WHERE id=%s' %skill_id)
    return s.fetchone()['name']

app.jinja_env.globals.update(get_activity_name=get_activity_name)
app.jinja_env.globals.update(get_activity_sessions=get_activity_sessions)
app.jinja_env.globals.update(get_skill_name=get_skill_name)




''' AJAX HELPERS '''
@app.route('/fetch_all_activities/<s_id>', methods=['GET','POST'])
def fetch_all_activities(s_id=None):
    app.logger.info("Getting activities where skill_id = %s" % s_id)
    activities = g.db.execute('SELECT * FROM activities WHERE skill_id = ? AND active=1', [s_id])
    d = {}
    for a in activities:
        d[str(a['id'])] = str(a['name'])
    app.logger.info("All activities through ajax: %s" % d)
    d = str(d).replace('\'', '\"')
    return d

@app.route('/fetch_one_activity/<a_id>', methods=['GET', 'POST'])
def fetch_one_activity(a_id=None):
    app.logger.info("Getting activity where activity_id = %s" % a_id)
    activities = g.db.execute('SELECT * FROM activities WHERE id=? AND active=1', [a_id])
    d = {}
    a = activities.fetchone()
    app.logger.info(a)
    for k, v in a.iteritems():
        d[str(k)]=str(v)
    d = str(d).replace('\'', '\"')
    app.logger.info("Activity info through ajax with id %s: %s" % (a_id, d))
    return d

if __name__ == '__main__':
    app.run()