from app import create_app

app = create_app()

if __name__ == "__main__":
    # FLASK_APP=app.py flask run --debug
    app.run(debug=True)