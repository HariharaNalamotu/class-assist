from flask import Flask, render_template, request, redirect, url_for
import csv
from flask_socketio import SocketIO
import base64
import datetime
import speech_recognition as sr
from transformers import pipeline
import os

global email

email = None

app = Flask(__name__)
socketio = SocketIO(app)

summarizer = pipeline("summarization")
r = sr.Recognizer()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def open_login():
    return render_template('login.html', text="")

@app.route('/login', methods=['POST'])
def login():
    global email
    email = request.form.get('email')
    password = request.form.get('password')
    with open("details/users.csv", 'r') as file:
        # Create a CSV DictReader
        reader = csv.DictReader(file)
        userExist = False
        for row in reader:
            if email == row["username"] and password == row["password"]:
                return redirect(url_for('create_dash'))
            elif email == row["username"] and password != row["password"]:
                userExist = True
    if userExist:
        return render_template("login.html", text="Password Incorrect")
    else:
        return render_template('login.html', text="Username not found")


@app.route("/dashboard", methods=['GET'])
def create_dash():
    global email
    global teacher
    with open("details/users.csv", 'r') as file:
        # Create a CSV DictReader
        reader = csv.DictReader(file)
        for row in reader:
            if email == row["username"]:
                if row["teacher"] == 'TRUE':
                    teacher = True
                else:
                    teacher = False
                classes = row["classes"].split(';')
                classes = classes[1:]
                return render_template("dashboard.html", classes=classes, teacher=teacher)

@app.route("/add")
def add():
    return render_template("add.html")

@app.route("/create", methods=['POST'])
def create_class():
    global email
    global className
    emails = request.form.get('emails')
    className = request.form.get("name")
    emails = emails.split(';')
    emails.append(email)
    with open('details/users.csv', 'r') as f:
        reader = csv.DictReader(f)
        data = [row for row in reader]
    for email in emails:
        for row in data:
            if row['username'] == email:
                # Get the current classes and split them into a list
                current_classes = row['classes'].split(';')

                # Add the new class if it's not already there
                if className not in current_classes:
                    current_classes.append(className)

                # Join the classes back into a string and update the row
                row['classes'] = ';'.join(current_classes)
                break

        # Write the data back to the CSV file
        with open('details/users.csv', 'w', newline='') as f:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

    with open(f'classes/{className}.csv', 'w', newline='') as f:
        fieldnames = ['date', 'transcript', 'summary']
        for email2 in emails[:-1]:
            fieldnames.append(email2)
        writer = csv.writer(f)
        writer.writerow(fieldnames)
    return redirect(url_for('create_dash'))

@app.route("/creatert", methods=['POST', 'GET'])
def create_class_rt():
    global className
    global email
    emails = request.form.get('emails')
    emails = emails.split(';')
    with open('details/users.csv', 'r') as f:
        reader = csv.DictReader(f)
        data = [row for row in reader]
    for email2 in emails:
        for row in data:
            if row['username'] == email2:
                # Get the current classes and split them into a list
                current_classes = row['classes'].split(';')

                # Add the new class if it's not already there
                if className not in current_classes:
                    current_classes.append(className)

                # Join the classes back into a string and update the row
                row['classes'] = ';'.join(current_classes)
                break

        # Write the data back to the CSV file
        with open('details/users.csv', 'w', newline='') as f:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

    with open(f'classes/{className}.csv', 'r') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        data = [row for row in reader]
    with open(f'classes/{className}.csv', 'w', newline='') as f:
        for email1 in emails:
            fieldnames.append(email1)
        for tuple in data[1:]:
            tuple[-1], tuple[-2] = 0
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    return redirect(url_for('create_dash'))

@app.route("/class", methods=["GET","POST"])
def make_class():
    global className
    global email
    global teacher
    className = request.form.get("buttonName")
    with open("details/users.csv", 'r') as file:
        # Create a CSV DictReader
        reader = csv.DictReader(file)
        for row in reader:
            if email == row["username"]:
                if teacher:
                    return render_template("class.html", className=className)
                else:
                    return redirect(url_for("lectures"))

@socketio.on('message')
def handle_message(data):
    global className
    global filename
    data1 = data.get('audio')
    data_url = data1.get('dataURL')
    encoded_data = data_url.split(',')[1]
    decoded_data = base64.b64decode(encoded_data)
    filename = f'audios/{className}{datetime.datetime.now().strftime("%H:%M:%S")}.wav'
    with open(f'audios/{className}{datetime.datetime.now().strftime("%H:%M:%S")}.wav', "wb") as audio_file:
        audio_file.write(decoded_data)

@app.route("/attendance", methods=["GET","POST"])
def attendance():
    global students
    global className
    with open(f"classes/{className}.csv", 'r') as f:
        reader = csv.reader(f)
        students = next(reader)[3:]
    return render_template("attendance.html", students=students, className = className)

@app.route("/attendance_rep", methods=["POST"])
def get_attendance():
    global students
    global className
    global filename
    global email
    with sr.AudioFile(filename) as source:
        # listen for the data (load audio to memory)
        audio_data = r.record(source)
        # recognize (convert from speech to text)
        text = r.recognize_google(audio_data)
        os.remove(filename)
    summary = summarizer(text, max_length=100, min_length=30, do_sample=False)
    register = {'date':datetime.datetime.now().date(),'transcript':text,'summary':summary[0]['summary_text']}
    for student in students:
        register[student] = request.form.get(student)
    with open(f'classes/{className}.csv', 'r') as f:
        reader = csv.DictReader(f)
        data = [row for row in reader]
        fieldnames = reader.fieldnames
    with open(f'classes/{className}.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        writer.writerow(register)
    return redirect(url_for('create_dash'))

@app.route("/lectures", methods = ["GET", 'POST'])
def lectures():
    global className
    global email
    with open(f'classes/{className}.csv', 'r') as file:
        rows = csv.reader(file)
        headers = next(rows)
        index = 0
        for header in headers:
            if header == email:
                break
            else:
                index += 1
        rows = list(rows)
        nrows = []
        rows.reverse()
        for row in rows:
            nrow = []
            nrow.append(row[0])
            if row[index] == 'on':
                nrow.append(True)
            else:
                nrow.append(False)
            nrows.append(nrow)
        rows = nrows
        return render_template("lectures.html", classes=rows, className=className)

@app.route("/summaries", methods=['GET', 'POST'])
def summaries():
    global className
    date = request.form.get("buttonName")
    with open(f"classes/{className}.csv") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["date"] == date:
                summary = row["summary"]
                return render_template('summaries.html', className=className, date=date, summary=summary)

@app.route('/register')
def open_register():
    return render_template('register.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    global email
    email = request.form.get("email")
    password = request.form.get("password")
    teacher = request.form.get("teacher")
    if teacher == "on":
        teacher = "TRUE"
    else:
        teacher = "FALSE"
    with open("details/users.csv") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["username"] == email:
                return render_template('register.html', text="Email already in use")
    with open("details/users.csv") as file:
        reader = csv.DictReader(file)
        data = [row for row in reader]
        fieldnames = reader.fieldnames
    with open(f'details/users.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        writer.writerow({"username": email, "password": password, "teacher": teacher})
    return redirect(url_for('create_dash'))


if __name__ == '__main__':
    app.run(debug=True)