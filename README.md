# ClatAI - AI-Powered CLAT Preparation Platform

A comprehensive web application designed to help students prepare for the Common Law Admission Test (CLAT) using AI-powered tools and resources.

## Features

- **GK Research Engine**: Generate GK passages and MCQs based on CLAT patterns
- **Lexa Chatbot**: AI assistant specialized in CLAT preparation
- **QT Mentor**: Quantitative aptitude question generator
- **Sectional Tests**: Practice tests for different CLAT sections
- **Progress Tracking**: Monitor your preparation progress
- **PDF Generation**: Download practice materials as PDFs

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **AI Integration**: Groq API
- **Deployment**: Render

## Environment Variables

Set the following environment variable in your Render dashboard:

- `GROQ_API_KEY`: Your Groq API key for AI functionality

## Deployment on Render

1. **Connect Repository**: Link your GitHub repository to Render
2. **Create Web Service**: Choose "Web Service" as the service type
3. **Configure Settings**:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Python Version**: 3.11.7
4. **Environment Variables**: Add `GROQ_API_KEY` with your API key
5. **Deploy**: Click "Create Web Service"

## Local Development

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd ClatAI
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variable**:
   ```bash
   export GROQ_API_KEY="your-groq-api-key"
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```

5. **Access the application**: Open http://localhost:5000

## API Endpoints

- `GET /` - Landing page
- `GET /health` - Health check
- `POST /gk/generate` - Generate GK content
- `POST /gk/assistant` - GK assistant chat
- `POST /lexa/chat` - Lexa chatbot
- `POST /qt/generate-question` - Generate QT questions
- `POST /generate-test` - Generate sectional tests
- `POST /api/generate-practice` - Generate practice questions

## File Structure

```
ClatAI/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── Procfile              # Render deployment configuration
├── runtime.txt           # Python version specification
├── 1.land.html          # Landing page
├── 2.homepage.html      # Homepage
├── gk-research.html     # GK Research Engine
├── lexa-chatbot.html    # Lexa Chatbot
├── qt-mentor.html       # QT Mentor
├── practice-online.html # Online practice
├── generate-tests.html  # Test generation
└── images/              # Static images
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.
