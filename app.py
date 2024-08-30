from flask import Flask, render_template, request
from transformers import pipeline
import numpy


print(numpy.__version__)
app = Flask(__name__)

# Initialize sentiment analysis pipeline
scoring_model_name = "nlptown/bert-base-multilingual-uncased-sentiment"
sentiment_model_name = "distilbert-base-uncased-finetuned-sst-2-english"
scoring_analyzer = pipeline("sentiment-analysis", model=scoring_model_name)
sentiment_analyzer = pipeline("sentiment-analysis", model=sentiment_model_name)

@app.route("/", methods=["GET", "POST"])
def index():
    sentiment_results = {}
    user_expected = {}
    if request.method == "POST":
        user_input = request.form["user_input"]
        user_rating = request.form["user_rating"]
        
        scoring_result = scoring_analyzer(user_input)[0]
        sentiment_results['scoring'] = {
            "label": scoring_result["label"],
            "score": round(scoring_result["score"], 4)
        }
        distilbert_result = sentiment_analyzer(user_input)[0]
        sentiment_results['sentiment'] = {
            "label": distilbert_result["label"],
            "score": round(distilbert_result["score"], 4)
        }
        user_expected = {
            "score": user_rating + " stars"
        }
        print(user_input)
    return render_template("index.html", sentiment_results=sentiment_results, user_expected=user_expected)

if __name__ == "__main__":
    app.run(debug=True)