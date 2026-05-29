from flask import Flask, render_template, request
import os
from PyPDF2 import PdfReader
from openai import OpenAI
from dotenv import load_dotenv

print("GROQ AI STUDY ASSISTANT RUNNING")

app = Flask(__name__)
stored_text = ""
load_dotenv()

# =========================
# UPLOAD FOLDER
# =========================

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# =========================
# GROQ CLIENT
# =========================

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

# =========================
# HOME PAGE
# =========================

@app.route("/")
def home():
    return render_template("index.html")


# =========================
# ABOUT PAGE
# =========================

@app.route("/about")
def about():
    return render_template("about.html")


# =========================
# UPLOAD PAGE
# =========================

@app.route("/upload", methods=["GET", "POST"])
def upload():
    global stored_text

    extracted_text = ""
    summary = ""

    if request.method == "POST":

        file = request.files["pdf_file"]

        if file:

            # =========================
            # SAVE FILE
            # =========================

            filepath = os.path.join(
                app.config["UPLOAD_FOLDER"],
                file.filename
            )

            file.save(filepath)

            # =========================
            # READ PDF
            # =========================

            pdf = PdfReader(filepath)

            for page in pdf.pages:

                text = page.extract_text()

                if text:
                    extracted_text += text
                    stored_text = extracted_text

            # =========================
            # AI SUMMARY
            # =========================

            try:

                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful AI study assistant."
                        },
                        {
                            "role": "user",
                            "content": f"""
                            Summarize these study notes clearly
                            for students in simple language.

                            Study Notes:

                            {extracted_text}
                            """
                        }
                    ],
                    temperature=0.5,
                    max_tokens=500
                )

                summary = response.choices[0].message.content
                quiz_response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful AI study assistant."
                        },
                        {
                            "role": "user",
                            "content": f"""
                            Create 5 quiz questions based on these study notes:

                            Study Notes:
                            Include:
                                    - Question
                                    - 4 options
                                    - Correct answer
                             nOTES:

                            {extracted_text}
                            """
                        }
                    ],
                    temperature=0.5,
                    max_tokens=500
                )
                
                
                quiz = quiz_response.choices[0].message.content
                
                                                

            except Exception as e:

                summary = f"AI Error: {str(e)}"

            return render_template(
                "upload.html",
                extracted_text=extracted_text,
                summary=summary,
                quiz=quiz
            )

    return render_template("upload.html")
@app.route("/chat", methods=["GET", "POST"])
def chat():

    answer = ""

    if request.method == "POST":

        question = request.form["question"]

        try:

            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "system",
                        "content": """
                        You are an AI study assistant.

                        Answer ONLY using the uploaded study notes.
                        """
                    },
                    {
                        "role": "user",
                        "content": f"""
                        Study Notes:

                        {stored_text}

                        Student Question:

                        {question}
                        """
                    }
                ],
                temperature=0.5,
                max_tokens=500
            )

            answer = response.choices[0].message.content

        except Exception as e:

            answer = f"AI Error: {str(e)}"

    return render_template(
        "chat.html",
        answer=answer
    )


# =========================
# RUN APP
# =========================

if __name__ == "__main__":
    app.run(debug=True)