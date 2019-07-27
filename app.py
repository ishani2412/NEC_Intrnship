from flask import *
from flask_oidc import OpenIDConnect
from okta import UsersClient
import jwt
import requests
from jwt.algorithms import RSAAlgorithm
import json
import mysql.connector


mysql = mysql.connector.connect(
  host="localhost",
  user="root",
  passwd="1234",
  database="HiringInceptors",
  auth_plugin="mysql_native_password"
)


app = Flask(__name__)
app.config["OIDC_CLIENT_SECRETS"] = "clients_secrets.json"
app.config["OIDC_COOKIE_SECURE"] = False
app.config["OIDC_CALLBACK_ROUTE"] = "/end/callback"
app.config["OIDC_SCOPES"] = ["openid", "email", "profile"]
app.config["OIDC_ID_TOKEN_COOKIE_NAME"]="oidc_token"
app.config["SECRET_KEY"] = "{{ LONG_RANDOM_STRING }}"


oidc = OpenIDConnect(app)
okta_client = UsersClient("https://dev-764808.okta.com", "00eyvjQ5-edxVO-whsoxWbORgbfr7kc--8cuSckLzZ")

def create_table():
    cur = mysql.cursor()
    cur.execute('create table if not exists job_list(job_id int(7) primary key Auto_Increment, job_title varchar(20), job_description varchar(200), job_skills varchar(20) );')
    cur.execute('create table if not exists resume( applicant_id varchar(10) ,  fullname varchar(30),education varchar(150) , phone varchar(11) ,email varchar(20),job_skills varchar(100),projects varchar(100), experience varchar(10));')
    cur.execute('create table if not exists status(job_id varchar(20),applicant_id varchar(20),status varchar(10));')



create_table()
def get_job_list():
    cursor=mysql.cursor()
    cursor.execute('select * from job_list where recruiter_id = %s ', [g.user.id])
    job_list=[]
    for x in cursor:
        job_list.append(x)

    return job_list


def convert(data):
    if isinstance(data, bytes):  return data.decode('ascii')
    return data


@app.before_request
def before_request():
    if oidc.user_loggedin:
        if oidc.get_access_token() is None:
            oidc.logout()
        else:
            g.user = okta_client.get_user(oidc.user_getfield("sub"))
            access_token=oidc.get_access_token()
            keys_respose=requests.get("https://dev-764808.okta.com/oauth2/default/v1/keys").content
            keys_respose=convert(keys_respose)
            keys_respose=json.loads(keys_respose)
            key_json = keys_respose['keys'][0];
            aud= "api://default"
            public_key = RSAAlgorithm.from_jwk(json.dumps(key_json))
            decoded = jwt.decode(access_token, public_key,audience=aud, algorithms='RS256')
            g.groups = decoded["groups"]
    else:
        g.user = None


@app.route("/")
@oidc.require_login
def index():
    return render_template("index.html")


@app.route("/dashboard")
@oidc.require_login
def dashboard():



  #  if 'recruiter' in g.groups:
     #   g.userRole = 'recruiter'
      #  return render_template("recruiter/recruiter_dashboard.html")
    if 'applicant' in g.groups:
        g.userRole = 'applicant'
        return render_template("applicant/applicant_dashboard.html")

@app.route("/login")
@oidc.require_login
def login():
    return redirect(url_for(".dashboard"))


@app.route("/logout")
def logout():
    oidc.logout()
    return redirect(url_for(".index"))


@app.route("/postJob", methods=['POST'])
@oidc.require_login
def postJob():
    if request.method == "POST":
        job_details = request.form
        job_title = job_details['jobTitle']
        job_description = job_details['jobDescription']
        job_skills = job_details['jobSkills']
        cur = mysql.cursor()
        cur.execute("INSERT INTO job_list(job_title, job_description, job_skills, recruiter_id) VALUES (%s, %s, %s, %s)", (job_title, job_description, job_skills, g.user.id))
        mysql.commit()
        cur.close()
    return redirect(url_for(".jobList"))


@app.route("/jobList", methods=['GET', 'POST'])
@oidc.require_login
def jobList():
    job_list = get_job_list()
    return render_template("recruiter/job_list.html", job_list = job_list)

@app.route("/get_applications", methods=['GET', 'POST'])
@oidc.require_login
def get_applications():
    cur = mysql.cursor()
    cur.execute("select * from status where job_id in (SELECT job_id from job_list where recruiter_id=%s)", [g.user.id])
    applications_list = []
    for x in cur:
        applications_list.append(x)


    return render_template("recruiter/applications_list.html", applications_list=applications_list)




# Applicant part

@app.route('/applicant_job_list')
@oidc.require_login
def applicant_job_list():
    cursor = mysql.cursor()
    cursor.execute("select * from job_list")

    return render_template("applicant/applicant_job_list.html", jobDetails=cursor)


@app.route('/apply_job',methods=['GET','POST'])
@oidc.require_login
def apply_job():

    job_id = request.form['apply']
    applicant_id = g.user.id
    status = "apply"
    cursor = mysql.cursor()
    cursor.execute(
        "INSERT INTO status(job_id, applicant_id,status) VALUES(%s,%s,%s)",
        (job_id, applicant_id, status))

    mysql.commit()
    cursor.close()
    return redirect(url_for(".applicant_job_list"))
@app.route('/create_resume',methods=['GET','POST'])
@oidc.require_login
def create_resume():
    applicant_id = g.user.id
    return render_template("applicant/applicant_details.html", applicant_id=applicant_id)


@app.route('/resume_handler', methods=['POST','GET'])
@oidc.require_login
def resume_handler():
    if request.method == "POST":
        applicant_details = request.form
        fname = applicant_details['fname']
        edu = applicant_details['education']
        phone = applicant_details['phone']
        email = applicant_details['email']
        applicant_id = applicant_details['applicant_id']
        proj = applicant_details['projects']
        exp = applicant_details['experience']
        job_skills = applicant_details['jobSkills']
        cursor = mysql.cursor()
        cursor.execute("INSERT INTO resume(applicant_id, fullname, education, phone , email, job_skills, projects,experience) VALUES(%s,%s,%s,%s, %s, %s,%s, %s)", (applicant_id, fname,edu, phone, email, job_skills, proj,exp))



        mysql.commit()
        cursor.close()
    return redirect(url_for(".dashboard"))
# app.run(debug=True)