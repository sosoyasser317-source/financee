import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
    rows = db.execute("SELECT symbol , SUM(shares) AS total_shares FROM transactions WHERE user_id = ? GROUP BY symbol HAVING total_shares > 0" , session["user_id"])
    grand_total = cash
    for row in rows:
        quote = lookup(row["symbol"])
        row["price"] = quote["price"]
        row["total"] = row["total_shares"] * quote["price"]
        grand_total += row["total"]
    return render_template("index.html" , cash=cash , rows=rows, grand_total=grand_total)
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    else:
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        if not symbol:
                return apology("invalid symbol", 400)
        stock = lookup(symbol)
        if not stock:
                return apology("invalid symbol", 400)
        if not shares or not shares.isdigit():
                return apology("invalid shares", 400)
        shares = int(shares)
        if shares <= 0:
                return apology("invalid shares", 400)
        price = stock["price"]
        total_cost = shares * price
        rows = db.execute("SELECT cash FROM users WHERE id = ?" , session["user_id"])
        user_cash = rows[0]["cash"]
        if user_cash < total_cost:
                return apology("invalid cost" , 400)
        db.execute("UPDATE users SET cash = cash - ? WHERE id = ? ", total_cost, session["user_id"])
        db.execute("INSERT INTO transactions (user_id , symbol , shares , price) VALUES(? , ? , ? , ?)", session["user_id"] , symbol.upper() , shares , price)
        return redirect("/")
@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = db.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY timestamp DESC", session["user_id"])
    return render_template("history.html", transactions=transactions)
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
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
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
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    elif request.method == "POST":
        symbol = request.form.get("symbol")
    if not symbol:
        return apology("must provide symbol", 400)
    look = lookup(symbol)
    if not look:
        return apology("invalid symbol", 400)

    return render_template("quoted.html" , look=look)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if not username:
           return apology("must provide username", 400)
        elif not password:
            return apology("must provide password", 400)
        elif not confirmation:
            return apology("must provide confirmation", 400)
        elif password != confirmation:
            return apology("passwords do not match", 400)
        hash = generate_password_hash(password)
        try:
            db.execute("INSERT  INTO users(username , hash) VALUES(? , ?)" , username , hash)
        except:
            return apology("username already taken", 400)
        return redirect("/")
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        symbols = db.execute("SELECT symbol FROM transactions WHERE user_id = ? GROUP BY symbol HAVING SUM(shares) > 0", session["user_id"])
        return render_template("sell.html", symbols=symbols)
    else:
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        if not symbol:
                return apology("invalid symbol" , 400)
        if not shares or not shares.isdigit():
                return apology("invalid shares", 400)
        shares = int(shares)
        user_shares = db.execute("SELECT SUM(shares) AS total_shares FROM transactions WHERE user_id = ? AND symbol = ? GROUP BY symbol", session["user_id"], symbol)
        if not user_shares or shares > user_shares[0]["total_shares"]:
                return apology("too many shares", 400)
        quote = lookup(symbol)
        price = quote["price"]
        total_sale = shares * price
        share_users = db.execute("INSERT INTO transactions (user_id , symbol , shares , price) VALUES(?,?,?,?)", session["user_id"], symbol , -shares , price)
        user = db.execute("UPDATE users SET cash = cash + ? WHERE id = ?",total_sale , session["user_id"])
        return redirect("/")

