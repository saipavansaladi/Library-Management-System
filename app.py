from flask import Flask,render_template,session,request,redirect,url_for
import pymongo,json,os
from datetime import datetime,timedelta

app=Flask(__name__)
app.secret_key='asdfghjkl'
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
try:
    mongo = pymongo.MongoClient(
        host = 'localhost',
        port = 27017,
        serverSelectionTimeoutMS = 1000
    )
    db = mongo['Project']
    mongo.server_info() #trigger exception if cannot connect to db
except:
    print("Error - connect to db")

def get_bookNamesbyISBN(data):
    result={}
    books_collection=db['Books']
    for i in data:
        t=books_collection.find_one({'isbn':str(i)})
        result[i]=t['title']
    return result

def get_bookNamesbyCopyID(data):
    result={}
    books_collection=db['Books']
    store_collection=db['Stores']
    isbn=[]
    for i in data:
        result[i]={}
        t=store_collection.find_one({'copyID':str(i)})
        isbn.append(t['isbn'])
        result[i]['isbn']=t['isbn']
        t=books_collection.find_one({'isbn':str(t['isbn'])})
        result[i]['title']=t['title']
    return result

def get_largest_userid():
    user_collection = db["Users"]
    pipeline = [
        {"$group": {"_id": None, "max_userid": {"$max": "$userId"}}}
    ]
    result = list(user_collection.aggregate(pipeline))
    largest_userid = result[0]['max_userid']
    return largest_userid

def get_largest_copyid():
    store_collection = db["Stores"]
    pipeline = [
        {"$group": {"_id": None, "max_copyid": {"$max": "$copyID"}}}
    ]
    result = list(store_collection.aggregate(pipeline))
    largest_copyid = int(result[0]['max_copyid'])
    return largest_copyid

def get_largest_reservationid():
    reserve_collection = db["Reservations"]
    pipeline = [
        {"$group": {"_id": None, "max_userid": {"$max": "$reservationID"}}}
    ]
    result = list(reserve_collection.aggregate(pipeline))
    if result:
        largest_reserveid = result[0]['max_userid']
    else:
        largest_reserveid=5000
    return largest_reserveid

def get_largest_transactionid():
    transaction_collection = db["Transactions"]
    pipeline = [
        {"$group": {"_id": None, "max_userid": {"$max": "$transaction_id"}}}
    ]
    result = list(transaction_collection.aggregate(pipeline))
    if result:
        largest_transactionid = result[0]['max_userid']
    else:
        largest_transactionid=4000
    return largest_transactionid

def get_largest_paymentid():
    payment_collection = db["Payments"]
    pipeline = [
        {"$group": {"_id": None, "max_userid": {"$max": "$paymentID"}}}
    ]
    result = list(payment_collection.aggregate(pipeline))
    if result:
        largest_paymentid = result[0]['max_userid']
    else:
        largest_paymentid=3000
    return largest_paymentid

def putBooksOnHold(books):
    store_collection=db['Stores']
    for i in books:
        store_collection.find_one_and_update({'isbn':str(i),'status':'available'},{'$set': {'status': 'onHold'}})

def getBooksOnHold(books):
    data={}
    store_collection=db['Stores']
    today=datetime.now().strftime("%Y-%m-%d")
    print("in")
    for i in books:
        print(i)
        id=store_collection.find_one({'isbn':str(i),'status':'onHold'},{'_id':0})
        data[id['copyID']]=today
    return data


@app.route("/register",methods=['GET','POST'])
def register():
    if request.method=='POST':
        fname=request.form['fname']
        lname=request.form['lname']
        email=request.form['email']
        password=request.form['password']
        phone=request.form['phone']
        membership=request.form['membership']
        address=request.form['address']

        user_collection = db["Users"]
        user_data = {
            "userId":get_largest_userid()+1,
            "first_name": fname,
            "last_name": lname,
            "email":email,
            "password":password,
            "phone":phone,
            "membership":membership,
            "address":address
        }
        user_collection.insert_one(user_data)
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route("/login",methods=['GET','POST'])
def login():
    if request.method=='POST':
        email = request.form['email']
        password = request.form['password']
        user_collection = db["Users"]
        user = user_collection.find_one({"email": email, "password": password})
        if user:
            session['user_id'] = user['userId']
            session['username'] = user_collection.find_one({'userId':session['user_id']})['first_name']
            return redirect(url_for('home'))
        else:
            return render_template('login.html',error='Invalid username or password')
    return render_template("login.html")

@app.route('/')
@app.route('/home')
def home():
    # session.clear()
    if 'user_id' in session:
        user_collection = db["Users"]
        user = user_collection.find_one({'userId':session['user_id']})
        return render_template("home.html",data=user['first_name'])
    else:
        return render_template("home.html")

@app.route('/Profile')
def Profile():
    user_collection = db["Users"]
    user = user_collection.find_one({'userId':session['user_id']})
    return render_template("profile.html",data=user)

@app.route('/signout')
def signout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/search',methods=['GET','POST'])
def search():
    if request.method=='POST':
        filterBy = request.form['filterBy']
        text=request.form['keyword']
        books_collection=db['Books']
        #print(session.get('clicked'))
        if text:
            regex_pattern = f".*{text}.*"
            query = {filterBy: {"$regex": regex_pattern, "$options": "i"}}
            books = list(books_collection.find(query,{'_id':0}))
            print(books)
            availability={}
            stores_collection=db['Stores']
            library_collection=db['Library']
            libraries=list(library_collection.find({},{'_id':0}))
            for i in books:
                availability[i['isbn']]=[]
                for j in libraries:
                    store=list(stores_collection.find({'isbn':i['isbn'],'status':'available','library_id':j['library_id']}))
                    if store:
                        availability[i['isbn']].append(j['library_id'])
            print(libraries)
            lib_names={}
            for i in libraries:
                lib_names[i['library_id']]=i['name']
            return render_template("search.html",books=books,availability=availability,libraries=lib_names)
    return render_template("search.html")

@app.route('/admin/addBooks',methods=['GET','POST'])
def add_books():
    library_collection=db['Library']
    libraries = list(library_collection.find({},{'_id':0}))
    if request.method=='POST':
        title=request.form['title']
        author=request.form['author']
        isbn=request.form['isbn']
        genre=request.form['genre']
        yop=request.form['yop']
        lib_id=request.form['library']
        print(lib_id)
        book_collection = db["Books"]
        book_data = {
            "title": title,
            "author": author,
            "genre":genre,
            "isbn":isbn,
            "yearofPublication":yop
        }
        result=book_collection.insert_one(book_data)
        store_collection=db['Stores']
        copy_data={
            "copyID": str(get_largest_copyid()+1),
            "isbn": isbn,
            "library_id": int(lib_id),
            "status": "available"
        }
        store_collection.insert_one(copy_data)
        file = request.files['file']
        filename = isbn+".jpg"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    return render_template("addBooks.html",libraries=libraries)

@app.route('/showBook/<string:isbn>')
def showBook(isbn):
    books_collection=db['Books']
    book = books_collection.find_one({'isbn':isbn},{'_id':0})
    # print(book)
    return render_template("showBook.html",book=book)

@app.route('/cart',methods=['GET','POST'])
def cart():
    if request.method=='POST':
        data=request.form.get('listData')
        # print(data)
        library_collection=db['Library']
        libraries = list(library_collection.find({},{'_id':0}))
        # print(libraries)
        return render_template("cart.html",data=json.loads(data),libraries=libraries)
    return render_template("cart.html")

@app.route('/cartSuccess',methods=['POST'])
def cartSuccess():
    if request.method=='POST':
        data1=request.form.get('myCart')
        # data2=request.form.get('library')
        reserve_collection = db["Reservations"]
        # print(type(session['user_id']))
        current_date_time = datetime.now()
        formatted_date = current_date_time.strftime("%Y-%m-%d")
        listofbooks=json.loads(data1)
        print(listofbooks)
        for i in listofbooks:
            books=[]
            books.append(int(i[0]))
            booksinHold=reserve_collection.find_one({"user_id":session['user_id'],"library_id":int(i[2])},{'_id':0})
            if booksinHold:
                newList=list(set(booksinHold['books']+books))
                reserve_collection.update_one({'user_id':session['user_id'],"library_id":int(i[2])},{'$set': {"books": newList}})
                putBooksOnHold(newList)
            else:
                reserve_data = {
                "reservationID":get_largest_reservationid()+1,
                "user_id": int(session['user_id']),
                "books": books,
                "library_id":int(i[2]),
                "reservation_date":formatted_date
                }
                reserve_collection.insert_one(reserve_data)
                putBooksOnHold(newList)
        return render_template("cartSuccess.html")

@app.route("/onhold")
def onhold():
    reserve_collection = db["Reservations"]
    library_collection=db["Library"]
    libraries={}
    data=list(library_collection.find())
    for i in data:
        libraries[i['library_id']]=i['name']
    data=list(reserve_collection.find({'user_id':session['user_id']},{'_id':0}))
    if data:
        books={}
        for i in data:
            books[i['library_id']]=get_bookNamesbyISBN(list(i['books']))
        return render_template("onhold.html",data=books,libraries=libraries)
    return render_template("onhold.html")

@app.route("/checkedout",methods=['GET','POST'])
def checkedout():
    transaction_collection = db["Transactions"]
    if request.method=='POST':
        data=transaction_collection.find_one({'user_id':session['user_id'],'type':'borrow'},{'_id':0,'copyIDs':1})
        copyid=request.form.get('copyID')
        listOfBooks=data['copyIDs']
        current_date_time = datetime.now()
        formatted_date = current_date_time.strftime("%Y-%m-%d")
        listOfBooks[copyid]=formatted_date
        print(listOfBooks)
        transaction_collection.update_one({'user_id':session['user_id'],'type':'borrow'},{'$set': {'copyIDs': listOfBooks}})
    data=transaction_collection.find_one({'user_id':session['user_id'],'type':'borrow'},{'_id':0,'copyIDs':1})
    if data:
        books=get_bookNamesbyCopyID(list(data['copyIDs']))
        # print(books)
        for i in data['copyIDs']:
            temp = datetime.strptime(data['copyIDs'][i], "%Y-%m-%d")
            date_after_14_days = temp + timedelta(days=14)
            books[i]['duedate']=date_after_14_days.strftime("%Y-%m-%d")
            diff=datetime.now()-date_after_14_days
            books[i]['finedin']=diff.days
        print(books)
        return render_template("checkedout.html",books=books,data=data['copyIDs'])
    return render_template("checkedout.html")

@app.route('/dues')
def dues():
    transaction_collection = db["Transactions"]
    data=transaction_collection.find_one({'user_id':session['user_id'],'type':'borrow'},{'_id':0,'copyIDs':1})
    if data:
        books=get_bookNamesbyCopyID(list(data['copyIDs']))
        # print(books)
        for i in data['copyIDs']:
            temp = datetime.strptime(data['copyIDs'][i], "%Y-%m-%d")
            date_after_14_days = temp + timedelta(days=14)
            books[i]['duedate']=date_after_14_days.strftime("%Y-%m-%d")
            diff=datetime.now()-date_after_14_days
            books[i]['finedin']=diff.days
        books_with_fine={}
        for i in books:
            if books[i]['finedin']>0:
                books_with_fine[i]=books[i]
        print(books)
        print(books_with_fine)
        return render_template("dues.html",books=books_with_fine,data=data['copyIDs'])
    return render_template("dues.html")

@app.route('/payment',methods=['POST'])
def payment():
    amount=int(request.form.get('total'))
    return render_template("payment.html",amount=amount)

@app.route('/paymentConfirm',methods=['POST'])
def paymentConfirm():
    amount=request.form.get('total')
    data={
        "user_id": session['user_id'],
        "paymentID": get_largest_paymentid()+1,
        "paymentMethod": "card",
        "amount": amount,
        "paymentDate": datetime.now().strftime("%Y-%m-%d"),
        "status": "success"
    }
    payment_collection=db['Payments']
    payment_collection.insert_one(data)
    transaction_collection=db['Transactions']
    transaction=transaction_collection.find_one({'user_id':session['user_id'],'type':'borrow'},{'_id':0})
    newData=transaction['copyIDs']
    for i in transaction['copyIDs']:
        newData[i]:datetime.now().strftime("%Y-%m-%d")
    transaction_collection.find_one_and_update({'user_id':session['user_id'],'type':'return'},{'$set': {'copyIDs':newData}})
    return render_template("paymentSuccess.html")

@app.route('/admin/login',methods=['GET','POST'])
def adminLogin():
    if request.method=='POST':
        username = request.form['email']
        password = request.form['password']
        admin_collection = db["admin"]
        admin = admin_collection.find_one({"username": username, "password": password})
        if admin:
            session['admin_id'] = admin['adminID']
            session['username'] = username
            session['library_id']=admin['library_id']
            return redirect(url_for('adminHome'))
        else:
            return render_template('adminLogin.html',error='Invalid username or password')
    return render_template("adminLogin.html")

@app.route('/admin')
@app.route('/admin/home')
def adminHome():
    return render_template("adminHome.html")

@app.route('/admin/getUserEmail')
def getUserEmail():
    return render_template('getUserEmail.html')

@app.route('/admin/getUserEmailReturn')
def getUserEmail2():
    return render_template('getUserEmail2.html')

@app.route('/admin/checkout',methods=['GET'])
def checkout():
    # email=request.form['email']
    # print(email)
    user_collection=db["Users"]
    user=list(user_collection.find({},{'_id':0}))
    # session['user_id']=user['userId']
    reserve_collection=db['Reservations']
    reservation=list(reserve_collection.find({},{'_id':0}))
    books={}
    users={}
    if reservation:
        for i in reservation:
            books.update(get_bookNamesbyISBN(i['books']))
            for k in user:
                if i['user_id']==k['userId']:
                    users[i['user_id']]=k['first_name']
        library_collection=db['Library']
        libraries=list(library_collection.find({},{'_id':0}))
        lib_names={}
        for i in libraries:
            lib_names[i['library_id']]=i['name']
        return render_template("checkoutUser.html",data=books,reservation=reservation,users=users,libraries=lib_names)
    return render_template("checkoutUser.html")

@app.route('/admin/checkoutSuccess',methods=['POST'])
def checkoutSuccess():
    reserve_id=request.form.get('id')
    reserve_collection=db['Reservations']
    reserve=reserve_collection.find_one({'reservationID':int(reserve_id)},{'_id':0})
    print(reserve)
    newData=getBooksOnHold(reserve['books'])
    transaction_collection=db['Transactions']
    transaction=transaction_collection.find_one({'user_id':reserve['user_id'],'type':'borrow'},{'_id':0})
    if not transaction:
        data={
                "transaction_id": get_largest_transactionid()+1,
                "user_id": reserve['user_id'],
                "type": "borrow",
                "copyIDs":newData,
                "payment_ids":[]
                }
        transaction_collection.insert_one(data)
    else:
        newData.update(transaction['copyIDs'])
        transaction_collection.find_one_and_update({'user_id':reserve['user_id'],'type':'borrow'},{'$set': {'copyIDs':newData}})
    reserve_collection.find_one_and_update({'user_id':reserve['user_id'],'library_id':reserve['library_id']},{'$set': {'books':[]}})
    return render_template("checkoutSuccess.html")

@app.route('/admin/return2',methods=['GET','POST'])
def return2():
    # email=request.form.get('email')
    # user_collection=db["Users"]
    # user=user_collection.find_one({'email':email},{'_id':0})
    # session['user_id']=user['userId']
    return render_template("bookReturn.html")

@app.route('/admin/return',methods=['GET','POST'])
def bookReturn():
    if request.method=='POST':
        id=request.form.get('code')
        transaction_collection=db['Transactions']
        transactions=list(transaction_collection.find({'type':'borrow'},{'_id':0}))
        store_collection=db['Stores']
        for transaction in transactions:
            newData=transaction['copyIDs']
            if id in transaction['copyIDs']:
                newData.pop(id,None)
                transaction_collection.find_one_and_update({'user_id':transaction['user_id'],'type':'borrow'},{'$set': {'copyIDs':newData}})
                transaction2=transaction_collection.find_one({'user_id':transaction['user_id'],'type':'return'},{'_id':0})
                if transaction2:
                    newData2=transaction2['copyIDs']
                    newData2[id]=datetime.now().strftime("%Y-%m-%d")
                    transaction_collection.find_one_and_update({'user_id':transaction['user_id'],'type':'return'},{'$set': {'copyIDs':newData2}})
                    store_collection.find_one_and_update({'copyID':id},{'$set': {'status':"available"}})
                    return render_template("bookReturn.html",msg="Success")
                data={
                "transaction_id": get_largest_transactionid()+1,
                "user_id": transaction['user_id'],
                "type": "return",
                "copyIDs": {
                    id: datetime.now().strftime("%Y-%m-%d")
                    },
                "payment_ids":[]
                }
                transaction_collection.insert_one(data)
                store_collection.find_one_and_update({'copyID':id},{'$set': {'status':"available"}})
                return render_template("bookReturn.html",msg="Success")
        return render_template("bookReturn.html",msg="Invalid code!")
    return render_template("bookReturn.html")

if __name__=='__main__':
    app.run(port=5000,debug=True)