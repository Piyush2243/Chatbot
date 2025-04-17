from flask import Flask, request, jsonify, render_template, session
import openai
import os
import PyPDF2
import docx
import requests
from bs4 import BeautifulSoup
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Set a secret key for session management

# Configure file uploads
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Azure OpenAI API Configuration
openai.api_type = "azure"
openai.api_base = "YOUR-AZURE-ENDPOINT"  # Replace with your Azure OpenAI endpoint
openai.api_version = "YOUR-AZURE-API-VERSION"
openai.api_key = "YOUR-AZURE-API-KEY"  # Replace with your Azure OpenAI API key

# Azure OpenAI Deployment Name
AZURE_DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME", "gpt-4")

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                text += extracted_text + "\n"
    return text

def extract_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_txt(txt_path):
    with open(txt_path, "r", encoding="utf-8") as file:
        return file.read()

def scrape_website(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return None
    soup = BeautifulSoup(response.text, "html.parser")
    return " ".join([p.text for p in soup.find_all("p")])

@app.route("/")
def home():
    session.clear()  # Clear session on page load
    return render_template("index.html")


@app.route("/get_response", methods=["POST"])
def get_response():
    try:
        user_message = request.form.get("query", "").strip()
        file = request.files.get("file")
        url = request.form.get("url", "").strip()
        
        context_text = ""

        # File handling
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)
            if filename.endswith(".pdf"):
                context_text = extract_text_from_pdf(file_path)
            elif filename.endswith(".docx"):
                context_text = extract_text_from_docx(file_path)
            elif filename.endswith(".txt"):
                context_text = extract_text_from_txt(file_path)

        # URL scraping
        elif url:
            context_text = scrape_website(url)
            if not context_text:
                return jsonify({"response": "Could not fetch content from the URL."}), 400

        # Store conversation history in session
        if "chat_history" not in session:
            session["chat_history"] = []
        
        # Add user message to history
        session["chat_history"].append({"role": "user", "content": user_message})

        # Construct full message list for OpenAI
        messages = [{"role": "system", "content": "You are a helpful assistant."}]
        messages.extend(session["chat_history"])
        
        if context_text:
            messages.append({"role": "system", "content": f"Context: {context_text}"})

        print("Sending to Azure OpenAI:", messages)  # Debugging

        # Request to Azure OpenAI
        response = openai.ChatCompletion.create(
            engine=AZURE_DEPLOYMENT_NAME,
            messages=messages
        )

        bot_reply = response["choices"][0]["message"]["content"]
        print("AI Response:", bot_reply)  # Debugging

        # Add bot reply to history
        session["chat_history"].append({"role": "assistant", "content": bot_reply})
        session.modified = True  # Mark session as modified

        return jsonify({"response": bot_reply})

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"response": f"Error: {str(e)}"}), 500

@app.route("/clear_session", methods=["POST"])
def clear_session():
    session.pop("chat_history", None)
    return jsonify({"message": "Session cleared."})

if __name__ == "__main__":
    app.run(debug=True, port=5001)
