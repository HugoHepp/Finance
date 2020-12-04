import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():

    # get user infos in variables
    userdata = db.execute("SELECT * FROM portfolio WHERE userid = :userid", userid = session["user_id"])
    userdatabis = db.execute("SELECT * FROM users WHERE id = :userid", userid = session["user_id"])
    usercash = round(userdatabis[0]["cash"],2)
    lenght = (len(userdata))


    #find grand total
    counter = usercash
    for i in range(lenght):
        counter = round(counter + userdata[i]["total"],2)

    #return template index
    return render_template("index.html", userdata = userdata , lenght = lenght, usercash = usercash , counter = counter)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "GET":
        return render_template("buy.html")
    else:
        #place lookup return in variables
        element = lookup(request.form.get("symbol"))
        if not element:
            return render_template("quoted.html" , search = element)
        price = element["price"]
        number = request.form.get("number")
        if not number :
            return apology("you must provide a positive whole number")
        if number.isdigit() == False:
            return apology("you must provide a positive whole number")
        if int(number) <= 0 :
            return apology("you must provide a positive whole number")
        finalpricetmp =  float(price)*float(number)
        finalprice = round(finalpricetmp,2)


        #get user cash from sql
        usercash = db.execute("SELECT cash FROM users WHERE id = :userid", userid = session["user_id"])


        #if item affordable
        if finalprice < usercash[0]["cash"]:
            today = date.today()
            db.execute("INSERT INTO history (userid, symbol, name, date, price, share, total, action) VALUES (:userid, :symbol, :name, :date, :price, :share, :total, :action)",userid = session["user_id"],  symbol = element["symbol"], name = element["name"], date = today , share = number, price = lookup(element["symbol"])["price"], total = finalprice, action = "Bought")
            #if item doesn't exist, create it in db
            if len(db.execute("SELECT symbol FROM portfolio WHERE userid = :userid AND symbol = :symbol", userid = session["user_id"], symbol = element["symbol"])) == 0:
                db.execute("UPDATE users SET cash = cash - :finalprice WHERE id =:userid", finalprice = finalprice, userid = session["user_id"])
                db.execute("INSERT INTO portfolio (userid, symbol, name, share, price, total) VALUES (:userid, :symbol, :name, :share, :price, :total)", userid = session["user_id"], symbol = element["symbol"], name = element["name"],share = number, price = lookup(element["symbol"])["price"], total = finalprice)
                return redirect("/")
            #if already exist, update it in db
            else:
                db.execute("UPDATE users SET cash = cash - :finalprice WHERE id =:userid", finalprice = finalprice, userid = session["user_id"])
                db.execute("UPDATE portfolio SET share = share + :share , price = :price , total = total + :total WHERE userid = :userid AND symbol = :symbol", share = number, price = price, total = finalprice ,userid = session["user_id"], symbol = element["symbol"])
                return redirect("/")
        #if not affordable
        else:
            return apology("Not enough money")




@app.route("/history")
@login_required
def history():

    #Find history for user in database then return template
    userdata = db.execute("SELECT * FROM history WHERE userid = :userid", userid = session["user_id"])
    lenght = (len(userdata))
    return render_template("history.html", userdata = userdata, lenght = lenght)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "GET":
        return render_template("quote.html")
    else:
        search = lookup(request.form.get("quote"))
        return render_template("quoted.html",search = search)





@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:

        #Safety check for inputs
        if not request.form.get("username"):
            return apology("Invalid username")

        elif not request.form.get("password"):
            return apology("Invalid password")

        elif request.form.get("confirmation") != request.form.get("password"):
            return apology("Passwords don't match")

        username = request.form.get('username')

        #Check database for doublons
        checkname =  db.execute("SELECT username FROM users WHERE username = :username",username = request.form.get('username'))
        if len(checkname) != 0:
            return apology("Username already taken..")

        #Create account
        else:
            password = generate_password_hash(request.form.get('password'))
            db.execute("INSERT INTO users (username, hash) VALUES (:username, :password)", username = username, password = password)
            return redirect("/")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "GET":
        return render_template("sell.html")
    else:
        sellelem = lookup(request.form.get("symbol"))

        #Safety check for input
        if not sellelem:
            return render_template("quoted.html" , search = sellelem)

        #Put data in variables
        sellprice = sellelem["price"]
        sellsymbol = sellelem["symbol"]
        sellname = sellelem["name"]
        sellnumber = request.form.get("number")

        #Safety check for input
        if not sellnumber :
            return apology("you must provide a positive whole number")
        if sellnumber.isdigit() == False:
            return apology("you must provide a positive whole number")
        if int(sellnumber) <= 0 :
            return apology("you must provide a positive whole number")


        #Calcul final price
        sellfinalprice = float(sellprice*int(sellnumber))

        #Check if user has enough shares in database
        sharecheck = db.execute("SELECT share FROM portfolio WHERE userid = :userid AND name = :name", userid = session["user_id"], name = sellname)
        if not sharecheck:
            return apology("Error on number")
        if (int(sharecheck[0]["share"])) >= int(sellnumber) :

            #Get date in variable
            today = date.today()

            #insert the transaction into history
            db.execute("INSERT INTO history (userid, symbol, name, date, price, share, total, action) VALUES (:userid, :symbol, :name, :date, :price, :share, :total, :action)",userid = session["user_id"],  symbol = sellsymbol, name = sellname, date  = today , share = sellnumber, price = lookup(sellsymbol)["price"], total = sellfinalprice, action = "Sold")
            #add cash to user
            db.execute("UPDATE users SET cash = cash + :sellfinalprice WHERE id =:userid", sellfinalprice = sellfinalprice, userid = session["user_id"])
            #remove shares of user
            db.execute("UPDATE portfolio SET share = share - :number WHERE userid = :userid AND name = :name", userid = session["user_id"], name = sellname , number = sellnumber)
            sharecheckbis = db.execute("SELECT share FROM portfolio WHERE userid = :userid AND name = :name", userid = session["user_id"], name = sellname)
            #remove from portfolio if user don't have share anymore
            if (sharecheckbis[0]["share"]) <= 0 :
                db.execute("DELETE FROM portfolio WHERE userid = :userid AND name = :name", userid = session["user_id"], name = sellname)


        else :
            return apology("Not enought shares")

    return redirect("/")




def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
