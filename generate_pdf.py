from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 15)
        self.cell(0, 10, 'HackerRank Orchestrate - AI Judge Interview Prep', ln=True, align='C')
        self.ln(10)

    def chapter_title(self, num, label):
        self.set_font('helvetica', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.multi_cell(0, 10, f"Q{num}: {label}", fill=True)
        self.ln(2)

    def chapter_body(self, body):
        self.set_font('helvetica', '', 11)
        self.multi_cell(0, 7, body)
        self.ln(8)

pdf = PDF()
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=15)

qa_pairs = [
    (
        "Why did you choose your specific Vision model and API over others?",
        "We chose Groq's Vision models (like Llama 3/4 Vision) for their extremely low latency and solid zero-shot image analysis capabilities. Given the challenge's constraint to build a functional system quickly, Groq provided the best balance of speed, cost (free tier), and reasoning quality for multi-modal evidence review."
    ),
    (
        "How did you handle the API rate limits and quotas?",
        "Groq's free tier has strict Requests Per Minute (RPM) limits which initially caused '429 Too Many Requests' errors. To solve this efficiently without wasting time on blind exponential backoff, we implemented a robust GroqClient wrapper. It handles proactive round-robin key rotation across multiple API keys. We paired this with a smart 15-second per-key cooldown, yielding a steady, delay-free throughput that completely eliminated rate limit hits during our final run."
    ),
    (
        "Did you encounter any image processing errors? How did you resolve them?",
        "Yes, we encountered opaque 'Invalid Image Data' (400) and 'Payload Too Large' (413) errors. Through debugging, we discovered two issues: (1) images exceeding Groq's 30-million pixel / 20MB limits, and (2) unsupported image formats like AVIF or WEBP masquerading as .jpg files. We implemented a preprocessing layer using the Pillow library to automatically downscale oversized images via Lanczos resampling and force-convert all unsupported formats to JPEG before base64 encoding."
    ),
    (
        "How did you ensure the model output was structured and parsable?",
        "We utilized the API's native JSON mode (response_format={\"type\": \"json_object\"}) combined with a highly structured prompt. We defined the exact JSON schema required for the claims prediction (claim_status, issue_type, severity, etc.) and enforced the output structure, eliminating the need for brittle Regex parsing."
    ),
    (
        "How did you utilize AI assistants during your development process?",
        "I pair-programmed with an AI coding assistant. The AI acted as a rapid prototyping partner. We collaboratively debugged the opaque API errors by writing analysis scripts, identified the hidden AVIF file formats, and co-wrote the Pillow image resizing logic. The AI was also instrumental in designing the multi-key round-robin rotation system to overcome the API rate limits smoothly."
    ),
    (
        "What was your approach to the multi-modal evidence review problem?",
        "Our approach was to treat it as a pipeline: (1) Ingestion and preprocessing of images to guarantee compatibility, (2) Formatting a structured prompt with the claims data and the images encoded in base64, (3) Request routing through our quota-managed client to the Vision Language Model, and (4) Parsing the deterministic JSON output into the final predictions CSV. We aimed for reliability and throughput over complex multi-agent reasoning."
    )
]

for i, (q, a) in enumerate(qa_pairs, 1):
    pdf.chapter_title(i, q)
    pdf.chapter_body(a)

pdf.output("AI_Judge_Interview_Prep.pdf")
print("PDF generated successfully.")
