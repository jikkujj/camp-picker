from flask import Flask, jsonify, render_template
import os
import json

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index_enhanced.html")


@app.route("/api/camps")
def get_camps():
    with open("frisco_camps_combined.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5001"))
    app.run(debug=True, host="0.0.0.0", port=port)
