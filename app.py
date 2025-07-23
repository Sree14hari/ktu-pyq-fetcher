from flask import Flask, request, jsonify, send_file
from bs4 import BeautifulSoup
from PyPDF2 import PdfMerger
import requests, os, tempfile

app = Flask(__name__)

BASE_URL = "http://202.88.225.92"

def get_pdf_link(detail_url):
    try:
        res = requests.get(detail_url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        link = soup.find("a", href=lambda x: x and "bitstream" in x)
        return BASE_URL + link['href'] if link else None
    except Exception as e:
        print("Error fetching PDF link:", e)
        return None

def search_pyqs(subject_code):
    search_url = f"{BASE_URL}/xmlui/simple-search?query={subject_code}"
    res = requests.get(search_url)
    soup = BeautifulSoup(res.text, 'html.parser')

    items = soup.select("div.artifact-title a")
    result = []
    for item in items:
        title = item.text.strip()
        detail_url = BASE_URL + item['href']
        pdf_url = get_pdf_link(detail_url)
        if pdf_url:
            result.append({
                "title": title,
                "pdf_url": pdf_url
            })

    return result

def download_and_merge_pdfs(results, subject_code):
    merger = PdfMerger()
    temp_files = []

    for r in results:
        try:
            pdf_response = requests.get(r['pdf_url'], timeout=10)
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            temp_file.write(pdf_response.content)
            temp_file.close()
            merger.append(temp_file.name)
            temp_files.append(temp_file.name)
        except Exception as e:
            print(f"❌ Failed to download {r['title']}: {e}")

    output_path = os.path.join(tempfile.gettempdir(), f"merged_{subject_code}.pdf")
    merger.write(output_path)
    merger.close()

    for file in temp_files:
        os.unlink(file)

    return output_path

@app.route("/merge", methods=["GET"])
def merge_endpoint():
    subject = request.args.get("subject")
    if not subject:
        return jsonify({"error": "subject code is required"}), 400

    results = search_pyqs(subject)
    if not results:
        return jsonify({"error": "no results found"}), 404

    merged_file = download_and_merge_pdfs(results, subject)
    return send_file(merged_file, as_attachment=True, download_name=f"merged_{subject}.pdf")

@app.route("/")
def index():
    return jsonify({"message": "✅ PYQ Backend API is running"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)  # use port 10000 for Render compatibility
