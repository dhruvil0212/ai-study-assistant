from flask import Flask, render_template, request, redirect, send_file,session
import os
from PyPDF2 import PdfReader
from openai import OpenAI
from dotenv import load_dotenv
from database import conn, cursor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


print("GROQ AI STUDY ASSISTANT RUNNING")

app = Flask(__name__)
app.secret_key = "supersecretkey"

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

@app.route("/register", methods=["GET", "POST"])
def register():

    message = ""

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]

        try:

            cursor.execute(
                """
                INSERT INTO users
                (username, password)

                VALUES (?, ?)
                """,
                (username, password)
            )

            conn.commit()

            return redirect("/login")

        except:

            message = "Username already exists."

    return render_template(
        "register.html",
        message=message
    )
@app.route("/login", methods=["GET", "POST"])
def login():

    message = ""

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]

        cursor.execute(
            """
            SELECT * FROM users
            WHERE username = ?
            AND password = ?
            """,
            (username, password)
        )

        user = cursor.fetchone()

        if user:

            session["user"] = username

            return redirect("/")

        else:

            message = "Invalid credentials."

    return render_template(
        "login.html",
        message=message
    )
@app.route("/logout")
def logout():

    session.pop("user", None)

    return redirect("/login")

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
    if "user" not in session:
     return redirect("/login")

    global stored_text

    extracted_text = ""
    summary = ""
    quiz = ""
    flashcards = ""

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

            # LIMIT HUGE PDFs
            extracted_text = extracted_text[:12000]

            stored_text = extracted_text

            try:

                # =========================
                # SINGLE AI REQUEST
                # =========================

                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {
                            "role": "system",
                            "content": """
                            You are an AI study assistant.

                            Generate content in EXACT format:

                            ===SUMMARY===
                            (summary here)

                            ===QUIZ===
                            (quiz here)

                            ===FLASHCARDS===
                            (flashcards here)
                            """
                        },
                        {
                            "role": "user",
                            "content": f"""
                            Study Notes:

                            {extracted_text}
                            """
                        }
                    ],
                    temperature=0.5,
                    max_tokens=1500
                )

                ai_output = response.choices[0].message.content

                # =========================
                # SPLIT AI SECTIONS
                # =========================

                parts = ai_output.split("===QUIZ===")

                if len(parts) > 1:

                    summary_part = parts[0]

                    quiz_flashcards = parts[1]

                    summary = summary_part.replace(
                        "===SUMMARY===",
                        ""
                    ).strip()

                    flash_parts = quiz_flashcards.split(
                        "===FLASHCARDS==="
                    )

                    if len(flash_parts) > 1:

                        quiz = flash_parts[0].strip()

                        flashcards = flash_parts[1].strip()

                # =========================
                # SAVE TO DATABASE
                # =========================

                cursor.execute(
                    """
                    INSERT INTO notes
                    (filename, extracted_text, summary, quiz, flashcards,username)

                    VALUES (?, ?, ?, ?, ?,?)
                    """,
                    (
                        file.filename,
                        extracted_text,
                        summary,
                        quiz,
                        flashcards,
                        session["user"]
                    )
                )

                conn.commit()

            except Exception as e:

                summary = f"AI Error: {str(e)}"

            return render_template(
                "upload.html",
                extracted_text=extracted_text,
                summary=summary,
                quiz=quiz,
                flashcards=flashcards
            )

    return render_template("upload.html")

# =========================
# CHAT PAGE
# =========================

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if "user" not in session:
        return redirect("/login")
    

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
# HISTORY PAGE
# =========================

@app.route("/history")
def history():

    if "user" not in session:
        return redirect("/login")

    cursor.execute(
        """
        SELECT * FROM notes
        WHERE username = ?
        ORDER BY id DESC
        """,
        (session["user"],)
    )

    notes = cursor.fetchall()

    return render_template(
        "history.html",
        notes=notes
    )
@app.route("/note/<int:note_id>")
def note_detail(note_id):

    if "user" not in session:
        return redirect("/login")

    cursor.execute(
        "SELECT * FROM notes WHERE id = ?",
        (note_id,)
    )

    note = cursor.fetchone()

    return render_template(
        "note_detail.html",
        note=note
    )
@app.route("/delete/<int:note_id>")
def delete_note(note_id):

    if "user" not in session:
        return redirect("/login")

    cursor.execute(
        "DELETE FROM notes WHERE id = ?",
        (note_id,)
    )

    conn.commit()

    return redirect("/history")
@app.route("/download/<int:note_id>")
def download_pdf(note_id):
    if "user" not in session:
        return redirect("/login")

    cursor.execute(
        "SELECT * FROM notes WHERE id = ?",
        (note_id,)
    )

    note = cursor.fetchone()

    filename = f"note_{note_id}.pdf"

    pdf = SimpleDocTemplate(filename)

    styles = getSampleStyleSheet()

    elements = []

    # =========================
    # TITLE
    # =========================

    elements.append(
        Paragraph(
            f"<b>{note[1]}</b>",
            styles['Title']
        )
    )

    elements.append(Spacer(1, 20))

    # =========================
    # SUMMARY
    # =========================

    elements.append(
        Paragraph(
            f"<b>AI Summary:</b><br/><br/>{note[3]}",
            styles['BodyText']
        )
    )

    elements.append(Spacer(1, 20))

    # =========================
    # QUIZ
    # =========================

    elements.append(
        Paragraph(
            f"<b>AI Quiz:</b><br/><br/>{note[4]}",
            styles['BodyText']
        )
    )

    elements.append(Spacer(1, 20))

    # =========================
    # FLASHCARDS
    # =========================

    elements.append(
        Paragraph(
            f"<b>AI Flashcards:</b><br/><br/>{note[5]}",
            styles['BodyText']
        )
    )

    # =========================
    # BUILD PDF
    # =========================

    pdf.build(elements)

    return send_file(
        filename,
        as_attachment=True
    )


# =========================
# RUN APP
# =========================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )