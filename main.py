from flask import Flask, render_template, request
from sqlalchemy import create_engine, text

app = Flask(__name__)

database = "mysql://b67bbd7798cce0:7fe3d541@us-cdbr-east-05.cleardb.net/heroku_44776ac56d8377e"
engine = create_engine(database, echo=True)
con = engine.connect()
current_id = 0
testID = 0
numQ = 0

@app.route('/', methods=['GET'])
def index():
    result = con.execute(text("select * from accounts")).all()
    return render_template('index.html', accounts=result)

@app.route('/', methods=['POST'])
def getID():
    global current_id
    if (request.form['id-num'] == ""):
        query = con.execute(text("insert into accounts (acc_type, firstname, lastname) values (:acc_type, :firstname, :lastname)"), request.form)
        return index()
    else:
        current_id = request.form['id-num']
        current_user = con.execute(text("select concat(firstname, ' ', lastname) as Name from accounts where id = " + current_id))
        for name in current_user:
            current_user = name.Name
        accountTypeQuery = con.execute(text("select acc_type from accounts where id = " + current_id))
        accountType = ""
        for type in accountTypeQuery:
            accountType = type
        if (accountType.acc_type == "Student"):
            return(students(current_user))
        else:
            return(teachers(current_user))

# @app.route('/teachers')
def teachers(name):
    global current_id
    result1 = con.execute(text("select * from tests where teacher = " + str(current_id))).all()
    print(result1)
    result2 = con.execute(text("select distinct test_id from tests_taken"))
    testIDList = []
    for row in result2:
        testIDList.append(row.test_id)

    submissionCounts = []
    for row in result1:
        if row.test_id in testIDList:
            submissionCounts.append(con.execute(text("select count(student) as count from tests_taken group by test_id")).all()[0].count)
        else:
            submissionCounts.append(0)
    return render_template('teachers.html', name=name, tests=result1, subCounts=submissionCounts)

# @app.route('/students')
def students(name):
    global current_id
    taken = []
    result2 = con.execute(text("select test_id, test_name, student, grade, teacher from tests_taken join tests using(test_id) where student = " + str(current_id))).all()
    for record in result2:
        taken.append(str(record.test_id))
    takenString = "0"
    for t in taken:
        if len(takenString) == 0:
            takenString += t
        else:
            takenString = takenString + " , " + t
    takenString = "(" + takenString + ")"
    result1 = con.execute(text("select * from tests where test_id not in " + takenString)).all()
    return render_template('students.html', tests=result1, taken=result2, name=name)

@app.route('/create_test', methods=["POST"])
def createTest():
    global testID
    global current_id
    global numQ
    con.execute(text("insert into tests (test_name, teacher, num_questions) values (:test_name, " + str(current_id) + ", :num_q)"), request.form)
    testID = con.execute(text("select test_id from tests order by test_id desc limit 1")).all()[0].test_id
    numQ = int(request.form['num_q'])
    return render_template('create_test.html', numQ=numQ, testName=request.form['test_name'], testID=int(testID))

@app.route('/create_questions', methods=["POST"])
def createQuestions():
    global current_id
    global testID
    global numQ
    for x in range(numQ):
        q = (request.form[f'q_input{x+1}'])
        con.execute(text(f"insert into questions values ({testID}, {x+1}, '{q}')"))
    current_user = con.execute(text("select concat(firstname, ' ', lastname) as Name from accounts where id = " + str(current_id)))
    for name in current_user:
        current_user = name.Name
    return teachers(current_user)

@app.route('/edit_test', methods=["POST"])
def editTest():
    global current_id
    con.execute(text(f"update questions set text = '{request.form['new_q']}' where test_id = " + str(int(request.form['test_id'])) + f" and question_num = {int(request.form['q_num'])}"), request.form)
    current_user = con.execute(text("select concat(firstname, ' ', lastname) as Name from accounts where id = " + str(current_id)))
    for name in current_user:
        current_user = name.Name
    return teachers(current_user)

@app.route('/delete_test', methods=["POST"])
def deleteTest():
    global current_id
    if (request.form['yes-no'] == 'yes'):
        con.execute(text("delete from answers where test_id = " + request.form['del_test_id']))
        con.execute(text("delete from tests_taken where test_id = " + request.form['del_test_id']))
        con.execute(text("delete from questions where test_id = " + request.form['del_test_id']))
        con.execute(text("delete from tests where test_id = " + request.form['del_test_id']))
    current_user = con.execute(text("select concat(firstname, ' ', lastname) as Name from accounts where id = " + str(current_id)))
    for name in current_user:
        current_user = name.Name
    return teachers(current_user)

@app.route('/take_test', methods=["POST"])
def takeTest():
    global current_id
    taken = []
    result2 = con.execute(text("select student from tests_taken where test_id = " + request.form['take_test_id'])).all()
    for record in result2:
        taken.append(str(record.student))
    if (request.form['yes-no'] == 'yes' and current_id not in taken):
        result = con.execute(text("select test_name, text, question_num from tests join questions using (test_id) where test_id = " + request.form['take_test_id'] + " order by question_num")).all()
        testName = result[0].test_name
        return render_template('test.html', test=result, testName=testName)
    else:
        current_user = con.execute(text("select concat(firstname, ' ', lastname) as Name from accounts where id = " + str(current_id)))
        for name in current_user:
            current_user = name.Name
        return students(current_user)

@app.route('/submit_test', methods=["POST"])
def submitTest():
    global current_id
    currentTest = con.execute(text("select test_id, num_questions from tests where test_name = '" + str(request.form['testName']) + "'")).all()
    currentTestID = currentTest[0].test_id
    currentMaxQ = currentTest[0].num_questions
    queryString = "insert into answers values (" + str(currentTestID) + ", " + str(current_id) + ", "
    for x in range(int(currentMaxQ)):
        con.execute(text(queryString + str(x+1) + ", '" + str(request.form['question' + str(x+1)]) + "')"))
    con.execute(text("insert into tests_taken values (" + str(currentTestID) + ", " + str(current_id) + ", " + "null)"))
    current_user = con.execute(text("select concat(firstname, ' ', lastname) as Name from accounts where id = " + str(current_id)))
    for name in current_user:
        current_user = name.Name
    return students(current_user)

@app.route('/view_subs', methods=["POST"])
def viewSubs():
    currentTestID = request.form["grade_test_id"]
    studentSubs = con.execute(text("select student, grade from tests_taken where test_id = " + str(currentTestID) + " order by student")).all()
    return render_template('view_submissions.html', submissions=studentSubs, currentTestID=currentTestID)

@app.route('/grade_test', methods=["POST"])
def gradeTest():
    currentTestID = request.form["grade_test_id"]
    student_id = request.form["student_id"]
    questions = con.execute(text("select question_num, text from questions where test_id = " + str(currentTestID))).all()
    print(questions)
    answers = con.execute(text("select text from answers where student = " + str(student_id) + " and test_id = " + str(currentTestID) + " order by question_num")).all()
    return render_template('grade_test.html', student=student_id, answers=answers, questions=questions, test=currentTestID)

@app.route('/submit_grade', methods=["POST"])
def submitGrade():
    currentTestID = request.form["grade_test_id"]
    student_id = request.form["student_id"]
    grade = request.form["grade"]
    con.execute(text("update tests_taken set grade = '" + grade + "' where student = " + str(student_id) + " and test_id = " + str(currentTestID)))
    studentSubs = con.execute(text("select student, grade from tests_taken where test_id = " + str(currentTestID) + " order by student")).all()
    return render_template('view_submissions.html', submissions=studentSubs, currentTestID=currentTestID)


if __name__ == '__main__':
    app.run(debug=True)