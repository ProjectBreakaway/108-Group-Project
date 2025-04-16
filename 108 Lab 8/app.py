from flask import Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "Hello, Flask!"

if __name__ == '__main__':    # Creates the database and tables
    app.run(debug=True)