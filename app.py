#Flask modules
from flask import Flask, render_template, request, flash, url_for, redirect, session
from flask_session import Session

#Database modules
import mysql.connector
import time
import datetime 
import json
import codecs

#Model modules
import random
from datetime import timedelta
from datetime import datetime

from transformers import TFBertModel
import pandas as pd
import numpy as np
from tqdm.auto import tqdm
import tensorflow as tf
from transformers import BertTokenizer

# Translation modules
from googletrans import Translator
translator = Translator(service_urls=['translate.google.com','translate.google.co.kr'])
translator = Translator()


# # Modules for music
import csv
# from youtubesearchpython import *

import urllib.request
import re

#Python Flask app 
app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.permanent_session_lifetime = timedelta(minutes=30)
Session(app)

# DATABASE 
mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password=""
)
mycursor = mydb.cursor()
database = "mini_proj_db"
mycursor.execute("CREATE DATABASE IF NOT EXISTS " + database)

mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password="",
  database = database
)

mycursor = mydb.cursor()

user_table = "CREATE TABLE IF NOT EXISTS Users \
 (username VARCHAR(25) NOT NULL, \
 name VARCHAR(50) NOT NULL, \
 age INT NOT NULL, \
 password VARCHAR(50) NOT NULL, \
 PRIMARY KEY(username));"

results_depression = "CREATE TABLE IF NOT EXISTS Depression \
 (username VARCHAR(25) NOT NULL, \
 time DATETIME NOT NULL, \
 result VARCHAR(20) NOT NULL, \
 dominant_emotion VARCHAR(20) NOT NULL, \
 PRIMARY KEY(username,time));"

results_anxiety = "CREATE TABLE IF NOT EXISTS Anxiety \
 (username VARCHAR(25) NOT NULL, \
 time DATETIME NOT NULL, \
 result VARCHAR(20) NOT NULL, \
 PRIMARY KEY(username,time));"

results_anger = "CREATE TABLE IF NOT EXISTS Anger \
 (username VARCHAR(25) NOT NULL, \
 time DATETIME NOT NULL, \
 result VARCHAR(20) NOT NULL, \
 PRIMARY KEY(username,time));"


user_insert = "INSERT INTO Users (username, name, age, password) \
 VALUES (%s, %s, %s, %s);"

dep_insert = "INSERT INTO Depression (username,time,result, dominant_emotion) \
 VALUES (%s,%s, %s, %s);"

anger_insert = "INSERT INTO Anger (username, time, result) \
 VALUES (%s, %s, %s);"

anxiety_insert = "INSERT INTO Anxiety (username,time, result) \
 VALUES (%s, %s, %s);"

mycursor.execute(user_table)

mycursor.execute(results_depression)

mycursor.execute(results_anger)

mycursor.execute(results_anxiety)

# ROUTES
@app.route('/')
# ‘/’ URL is bound with hello_world() function.
def hello_world():
	return render_template("index.html")

@app.route('/login')
def login_page():
	return render_template("login.html")


@app.route('/signup')
def sign_page():
	return render_template("signup.html")

@app.route('/chat')
def chat_page():
	if not session.get("username"):
		return redirect("/login")
	return render_template("chat.html")


@app.route('/new_chat')
def new_chat_page():
	if not session.get("username"):
		return redirect("/login")
	session["info"] =  {"pos" : 0, "neg" : 0, "cur" : 0,  "responses" : [], "per" : "", "anx" : 0,"ang":0 , "emotions" : {"joy" : 0, "sad":0, "anger":0, "guilt":0, "fear":0, "shame":0, "disgust":0}}

	return render_template("new_chat.html")


@app.route('/sign_submit', methods=['POST'])
def sign_sumbit_page():
	if request.method == 'POST':
		message = ""
		username = request.form.get('username')
		name = request.form.get('name')
		pass1 = request.form.get('pass1')
		pass2 = request.form.get('pass2')
		age = request.form.get('age')

		

		select_user = "SELECT * FROM Users WHERE username = '" + username + "'"

		mycursor.execute(select_user)

		myuser = mycursor.fetchall()

		if len(myuser)>0:
			message = "Username already exists! Please enter something else."
		
		elif pass1 != pass2:
			message = "Passwords don't match! Please enter the passwords again."

		else:
			values = (username, name, age, pass1)
			
			mycursor.execute(user_insert, values)
			mydb.commit()
			if(mycursor.rowcount==1):
				message = "User registered successfully :)"
				flash(message)
				time.sleep(2)
				return redirect(url_for('login_page'))
				# return render_template("login.html")
			else:
				message = "Some error occurred :( Please try again!"
				return render_template("signup.html")
		# print(message)


@app.route('/login_submit', methods=['POST'])
def login_sumbit_page():
	if request.method == 'POST':
		message = ""
		username = request.form.get('username')
		pass1 = request.form.get('pass1')
		
		select_user = "SELECT * FROM Users WHERE username = '" + username + "'"

		mycursor.execute(select_user)

		myuser = mycursor.fetchall()

		if len(myuser)>0:
			if myuser[0][3] == pass1:
				message = "Logged in successfully :)"
				session["username"] = username
				
				session["name"] = translator.translate(myuser[0][1], dest='hi').text
				session["info"] =  {"pos" : 0, "neg" : 0, "cur" : 0,  "responses" : [], "per" : "", "anx" : 0,"ang":0, "emotions" : {"joy" : 0, "sad":0, "anger":0, "guilt":0, "fear":0, "shame":0, "disgust":0}}
				print(session["info"]["pos"])
				return render_template("/chat.html")

			else:
				message = "Wrong password!"
				return render_template("login.html")

		else:
			message = "User not found!"
			return render_template("login.html")

@app.route('/check')
def check_page():
	return render_template("check.html")



### Model ###	
sentiment_model = tf.keras.models.load_model('sentiment_model')
tokenizer = BertTokenizer.from_pretrained('bert-base-cased')

def prepare_data(input_text, tokenizer):
    token = tokenizer.encode_plus(
        input_text,
        max_length=256, 
        truncation=True, 
        padding='max_length', 
        add_special_tokens=True,
        return_tensors='tf'
    )
    return {
        'input_ids': tf.cast(token.input_ids, tf.float64),
        'attention_mask': tf.cast(token.attention_mask, tf.float64)
    }

def make_prediction(model, processed_data, classes=['Joy', 'Anger', 'Sadness', 'Fear', 'Disgust', 'Shame', 'Guilt']):
    probs = model.predict(processed_data)[0]
    return classes[np.argmax(probs)]
	

@app.route('/check_submit', methods=['POST'])
def check_sumbit_page():
	if request.method == 'POST':
		label = ""
		input_text = request.form.get('input')
		processed_data = prepare_data(input_text, tokenizer)
		result = make_prediction(sentiment_model, processed_data=processed_data)
		print(f"Predicted Sentiment: {result}")
		return render_template("index.html")


# info = {"pos" : 0, "neg" : 0, "test" : "", "cur" : 0,  "responses" : [], "per" : "", "anx" : 0,"ang":0 }

@app.route('/activities')
def activities_page():
	if not session.get("username"):
		return redirect("/login")
	return render_template("activities.html")

# @app.route('/start')
# def start():
# 	print("hello clicked")
# 	info['test'] = "depression"
# 	return "hi"


# @app.route('/route_button', methods=['POST', 'GET'])
# def route_button_page():
# 	global info
# 	print(request.method)
# 	args = request.args
# 	info["test"] = args['button']
# 	print(info["test"])
# 	return ""


@app.route('/get-bot-response', methods=['POST', 'GET'])
def get_bot_response():
	# global info
	input_text_hindi = request.args.get('msg')
	input_text = translator.translate(input_text_hindi, dest='en').text
	print(input_text)
	
	processed_data = prepare_data(input_text, tokenizer)
	result = make_prediction(sentiment_model, processed_data=processed_data)
	# info["responses"].append(result)
	session["info"]["responses"].append(result)
	
	print(result)
	f = open('depression.json', encoding='utf-8')
	data = json.load(f)
	res = {"message" : "Hello", "hidden" : "true", "buttons" : [], "neg_response" : "false"}
	
	# if(info['cur']<10):
	# 	res = data["depression"][info['cur']]["question"]
	# 	info['cur'] = info['cur'] +  1
	# if(result=="Joy"):
	# 	return " ये तो अच्छी बात है "+ "<br>" +res
	# elif(result=="Sadness"):
	# 	return "बुरा हुआ"+"<br>"+res
	# elif(result=="Anger"):
	# 	return "क्रोधित न हों"+"<br>"+res
	# elif(result=="Fear"):
	# 	return "डरो मत"+"<br>"+res
	# elif(result=="Shame" or result=="Disgust" ):
	# 	return "चिंता मत करो"+"<br>"+res
	# return res

	mess = ""
	response = "" 
	res["redirect"] = "false"
	res["redirect_url"] = ""
	result_ = ""
	if(session["info"]['cur']<10):
		mess = data["depression"][session["info"]['cur']]["question"]
		response = data["depression"][session["info"]['cur']]["response"]
		session["info"]['cur'] = session["info"]['cur'] +  1
	elif session["info"]['cur']==10:
		if(session["info"]['pos']>0):
			result_ =  str(session["info"]['pos'])+"%" + " " + "positive"
			res['message']= "अलविदा !!!"
		elif(session["info"]['pos']<0):
			result_ = str(((-1)*session["info"]['pos']))+"%" + " " + "negative"
			res['message']= "अलविदा !!!"
		else :
			result_ = "neutral"
			res['message']='अलविदा !!!'

		session["info"]["per"] = result_
		res["redirect"] = "true"
		res["redirect_url"] = "/activities"

		

		values = (session["username"], datetime.now(),result_ ,"")
		mycursor.execute(dep_insert, values)
		mydb.commit()
		return res

	print(input_text_hindi)
	if(input_text_hindi == "no_response_from_user"):
		mess = " ये तो अच्छी बात है "+ "<br>" + mess
	elif(result=="Joy"):
		session["info"]["emotions"]["joy"] += 1
		mess = " ये तो अच्छी बात है "+ "<br>" + mess
		session["info"]['pos']=session["info"]['pos']+10
	elif(result=="Sadness"):
		session["info"]["emotions"]["sad"] += 1
		mess =  "बुरा हुआ"+"<br>"+mess
		session["info"]['pos']=session["info"]['pos']-10
	elif(result=="Anger"):
		session["info"]["emotions"]["anger"] += 1
		mess =  "क्रोधित न हों"+"<br>"+mess
		session["info"]['pos']=session["info"]['pos']-5
	elif(result=="Fear"):
		session["info"]["emotions"]["fear"] += 1
		mess =  "डरो मत"+"<br>"+mess
		session["info"]['pos']=session["info"]['pos']-10
	elif(result=="Disgust" or result=="Guilt"):
		if result=="Disgust":
			session["info"]["emotions"]["disgust"] += 1
		else:
			session["info"]["emotions"]["guilt"] += 1
		mess =  "चिंता मत करो"+"<br>"+mess
		session["info"]['pos']=session["info"]['pos']-5
	elif(result=="Shame"):
		session["info"]["emotions"]["shame"] += 1
		mess =  "घबराओ मत"+"<br>"+mess
		session["info"]['pos']=session["info"]['pos']-5
	res["message"] = mess

	
	if(response!=""):
		res["hidden"] = "false"
		res["neg_response"] = response
		res["buttons"].append("हाँ")
		res["buttons"].append("नहीं")
	return res

@app.route('/log_out', methods=['POST', 'GET'])
def log_out_page():
	for key in list(session.keys()):
		session.pop(key)
	return redirect(url_for('hello_world'))


@app.route('/anxiety', methods=['POST', 'GET'])
def anxiety_page():
	if not session.get("username"):
		return redirect("/login")
	session["info"] =  {"pos" : 0, "neg" : 0, "cur" : 0,  "responses" : [], "per" : "", "anx" : 0,"ang":0 , "emotions" : {"joy" : 0, "sad":0, "anger":0, "guilt":0, "fear":0, "shame":0, "disgust":0}}

	return render_template("anxiety.html")
	

@app.route('/get-bot-response-anxiety', methods=['POST', 'GET'])
def anxiety_response_page():
	# global info
	res = {"message" : "Hello", "hidden" : "true", "buttons" : []}
	index = request.args.get('reply')
	result_ = ""
	if(index=='0'):
		session["info"]['anx']=session["info"]['anx']+10
	elif(index=='1'):
		session["info"]['anx']=session["info"]['anx']+5
	elif(index=='3'):
		session["info"]['anx']=session["info"]['anx']-5
	elif(index=='4'):
		session["info"]['anx']=session["info"]['anx']-10
	if session["info"]['cur']==10:
		if(session["info"]['anx']>0):
			result_ =  str(session["info"]['pos'])+"%" + " " + "positive"
			res['message']= "अलविदा !!!"
		elif(session["info"]['anx']<0):
			res['message']= "अलविदा !!!"
			result_=str(((-1)*session["info"]['anx']))+"%" + " " + "negative"
		else :
			res['message']='अलविदा !!!'
			result_ = "neutral"
		session["info"]["per"] = result_
		res["redirect"] = "true"
		res["redirect_url"] = "/activities"
		values = (session["username"], datetime.now(),result_)
		mycursor.execute(anxiety_insert, values)
		mydb.commit()



		return res
	# if info["cur"] == 0 and (input_text == "na" or input_text == "nahi" or input_text == "nai" or input_text == "naa" or input_text == "jee nahi" or input_text == "ji nahi" or input_text == "ji nai"):
	# 	info["cur"] = 100

	
	f = open('anxiety.json', encoding='utf-8')
	data = json.load(f)
	

	mess = ""
	response = "" 
	res["redirect"] = "false"
	res["redirect_url"] = ""
	if(session["info"]['cur']<10):
		mess = data["anxiety"][session["info"]['cur']]["question"]
		session["info"]['cur'] = session["info"]['cur'] +  1
		resp = data["anxiety"][session["info"]['cur']]['response']
		res["hidden"] = "false"
		for i in resp:
			res["buttons"].append(i)
		res["message"] = mess
	return res

@app.route('/anger', methods=['POST', 'GET'])
def anger_page():
	if not session.get("username"):
		return redirect("/login")
	session["info"] =  {"pos" : 0, "neg" : 0, "cur" : 0,  "responses" : [], "per" : "", "anx" : 0,"ang":0, "emotions" : {"joy" : 0, "sad":0, "anger":0, "guilt":0, "fear":0, "shame":0, "disgust":0} }

	return render_template("anger.html")


@app.route('/get-bot-response-anger', methods=['POST', 'GET'])
def anger_response_page():
	# global info
	res = {"message" : "Hello", "hidden" : "true", "buttons" : []}
	index = request.args.get('reply')
	result_ = ""
	if(index=='0'):
		session["info"]['ang']=session["info"]['ang']+10
	elif(index=='1'):
		session["info"]['ang']=session["info"]['ang']+5
	elif(index=='3'):
		session["info"]['ang']=session["info"]['ang']-5
	elif(index=='4'):
		session["info"]['ang']=session["info"]['ang']-10
	if session["info"]['cur']==10:
		if(session["info"]['ang']>0):
			result_ = str(session["info"]['ang'])+"%" + " " + "positive"
			res['message']="अलविदा !!!"
		elif(session["info"]['ang']<0):
			result_ = str(((-1)*session["info"]['ang']))+"%" + " " + "negative"
			res['message']="अलविदा !!!"
		else :
			result_ = "neutral"
			res['message']='अलविदा !!!'
		session["info"]["per"] = result_
		res["redirect"] = "true"
		res["redirect_url"] = "/activities"
		values = (session["username"],datetime.now(),result_)
		mycursor.execute(anger_insert, values)
		mydb.commit()

		return res
	# if info["cur"] == 0 and (input_text == "na" or input_text == "nahi" or input_text == "nai" or input_text == "naa" or input_text == "jee nahi" or input_text == "ji nahi" or input_text == "ji nai"):
	# 	info["cur"] = 100

	
	f = open('anger.json', encoding='utf-8')
	data = json.load(f)
	

	mess = ""
	response = "" 
	res["redirect"] = "false"
	res["redirect_url"] = ""
	if(session["info"]['cur']<10):
		mess = data["anger"][session["info"]['cur']]["question"]
		session["info"]['cur'] = session["info"]['cur'] +  1
		resp = data["anger"][session["info"]['cur']]['response']
		res["hidden"] = "false"
		for i in resp:
			res["buttons"].append(i)
		res["message"] = mess
	return res


@app.route('/ask-reason', methods=['POST', 'GET'])
def ask_reason_page():
	user_response = request.args.get('user_response')
	neg_response = request.args.get('neg_response')
	res = {"reason" : ""}
	if(user_response == neg_response):
		f = open('reason.json', encoding='utf-8')
		data = json.load(f)
		n = random.randint(0,6)
		reason = data['reason'][n]['question']
		res["reason"] = reason
		# info['pos'] -= 5
	else:
		session["info"]['pos'] += 10
		session["info"]["emotions"]['joy'] += 1
	return res
	
	
@app.route('/history', methods=['POST', 'GET'])
def history_page():
	if not session.get("username"):
		return redirect("/login")

	return render_template("history.html")

@app.route('/angerhistory', methods=['POST', 'GET'])
def anger_history_page():
	if not session.get("username"):
		return redirect("/login")

	return render_template("angerhistory.html")

@app.route('/anxietyhistory', methods=['POST', 'GET'])
def anxiety_history_page():
	if not session.get("username"):
		return redirect("/login")

	return render_template("anxietyhistory.html")


@app.route('/getDepression', methods=['GET'])
def getDepression():
	if not session.get("username"):
		return redirect("/login")
	select_user = "SELECT * FROM depression WHERE username = '" + session['username'] + "'"
	mycursor.execute(select_user)
	myuser = mycursor.fetchall()
	
	result={'depress': [],'anxiety':[],'anger':[]}
	for x in myuser :
		date_time_str = str(x[1])
		x_date= datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
		date = x_date.strftime("%A, %d %B, %Y")
		date_hindi = translator.translate(date, src="en", dest='hi').text


		result['depress'].append({'time':date_hindi, 'result':x[2],'dominant':x[3]})
	select_anxiety = "SELECT * FROM anxiety WHERE username = '" + session['username'] + "'"
	mycursor.execute(select_anxiety)
	myanxiety = mycursor.fetchall()

	
	for x in myanxiety :
		date_time_str = str(x[1])
		x_date= datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
		date = x_date.strftime("%A, %d %B, %Y")

		date_hindi = translator.translate(date, src="en", dest='hi').text

		result['anxiety'].append({'time':date_hindi, 'result':x[2]})
	select_anger = "SELECT * FROM anger WHERE username = '" + session['username'] + "'"
	mycursor.execute(select_anger)
	myanger = mycursor.fetchall()
	
	for x in myanger :
		date_time_str = str(x[1])
		x_date= datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
		date = x_date.strftime("%A, %d %B, %Y")
		date_hindi = translator.translate(date, src="en", dest='hi').text

		result['anger'].append({'time':date_hindi, 'result':x[2]})
		
	return result


@app.route('/getActivities', methods=['POST', 'GET'])
def get_activity_page():
	if not session.get("username"):
		return redirect("/login")

	f = open('activities.json', encoding='utf-8')
	data = json.load(f)

	activities = data["activities"]
	
	random.shuffle(activities)

	result = {"activities" : []}

	result["activities"] = activities[:5]

	return result

@app.route('/getEmotions', methods=['POST', 'GET'])
def get_emotions_page():
	if not session.get("username"):
		return redirect("/login")
	
	result = {"emotions" : {}, "per" : ""}
	result['emotions'] = session["info"]["emotions"]
	result["per"] = session["info"]["per"]
	return result
	



@app.route("/getnewmusic", methods=["POST", "GET"])
def get_music_new_page():
	genre = request.args.get('genre').lower()
	songs = []
	with open('bollywood_songs.csv', 'r') as file:
		reader = csv.reader(file)
		for row in reader:
			if row[3].lower().find(genre) != -1:
				songs.append(row)
				
	random.shuffle(songs)
	songs = songs[:20]
	result = {"links" : [], "titles" : [], "artists" : []}
	for song in songs:
		hindi_title = translator.translate(song[1], src="en", dest='hi').text
		hindi_artist = translator.translate(song[2], src="en", dest='hi').text
		result["titles"].append(hindi_title)
		result["artists"].append(hindi_artist)
		result["links"].append(song[6])
		
	return result






# @app.route("/getnewmusic", methods=["POST", "GET"])
# def get_music_new_page():
# 	genre = request.args.get('genre').lower()
# 	songs = []
# 	with open('songs.csv', 'r') as file:
# 		reader = csv.reader(file)
# 		for row in reader:
# 			if row[3].lower().find(genre) != -1:
# 				songs.append(row)
				
# 	random.shuffle(songs)
# 	songs = songs[:20]
# 	result = {"links" : [], "titles" : [], "artists" : []}	
# 	for song in songs:
# 		search_keyword= song[1]
# 		listt = search_keyword.split(" ")

# 		keywords = '+'.join(map(str, listt))

# 		# print(keywords)
# 		keywords.replace(u"\u2013", "-")
		
# 		keywords = re.sub(r'[^\x00-\x7F]+','', keywords)
# 		html = urllib.request.urlopen("https://www.youtube.com/results?search_query=" + keywords)

# 		# print(html)
# 		video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
		
# 		you_link = "https://www.youtube.com/watch?v=" + video_ids[0]
# 		result["links"].append(you_link)
	

# 		hindi_title = translator.translate(song[1], src='en', dest='hi').text
# 		hindi_artist = translator.translate(song[2],src='en', dest='hi').text

# 		result["titles"].append(hindi_title)
# 		result["artists"].append(hindi_artist)
	
# 	return result


# @app.route("/getMusic", methods=["GET"])
# def get_music_page():
# 	if request.method == 'GET':
# 		genre = request.args.get('genre').lower()
# 		songs = []

# 		with open('songs.csv', 'r') as file:
# 			reader = csv.reader(file)
# 			for row in reader:
# 				if row[3].lower().find(genre) != -1:
# 					songs.append(row)

# 		random.shuffle(songs)
# 		songs = songs[:20]
# 		result = {"links" : [], "titles" : [], "artists" : []}	

# 		for song in songs:
# 			videosSearch = VideosSearch(song[1] + " " + song[2], limit = 1)
# 			result["links"].append(videosSearch.result()['result'][0]['link'])
# 			result["titles"].append(song[1])
# 			result["artists"].append(song[2])

# 		return result


@app.route('/songs', methods=['POST', 'GET'])
def get_songs_page():
	return render_template("songs.html")


# @app.route("/analyze-user-response", methods = ["POST", "GET"])
# def analyze_user_response():
# 	userText = request.args.get('msg')
# 	input_text = request.form.get('input')
# 	processed_data = prepare_data(input_text, tokenizer)
# 	result = make_prediction(sentiment_model, processed_data=processed_data)
# 	global info
# 	info["responses"].append(result)
# 	# print(result)
# 	return result
    

# main driver function
if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0',port=8000)

