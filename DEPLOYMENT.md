# ClatAI Deployment Guide for Render

This guide will help you deploy your ClatAI application to Render.

## Prerequisites

1. **Groq API Key**: Get your API key from [Groq Console](https://console.groq.com/)
2. **GitHub Repository**: Your code should be in a GitHub repository
3. **Render Account**: Sign up at [Render.com](https://render.com/)

## Step-by-Step Deployment

### 1. Prepare Your Repository

Make sure your repository contains these files:
- `app.py` - Main Flask application
- `requirements.txt` - Python dependencies
- `Procfile` - Render deployment configuration
- `runtime.txt` - Python version specification
- All HTML files and static assets

### 2. Connect to Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" and select "Web Service"
3. Connect your GitHub repository
4. Select the repository containing your ClatAI code

### 3. Configure the Web Service

**Basic Settings:**
- **Name**: `clatai` (or your preferred name)
- **Environment**: `Python 3`
- **Region**: Choose closest to your users
- **Branch**: `main` (or your default branch)

**Build & Deploy Settings:**
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`

**Advanced Settings:**
- **Auto-Deploy**: Enable (recommended)
- **Health Check Path**: `/health`

### 4. Set Environment Variables

In the Render dashboard, go to "Environment" tab and add:

```
GROQ_API_KEY=your_groq_api_key_here
```

Replace `your_groq_api_key_here` with your actual Groq API key.

### 5. Deploy

1. Click "Create Web Service"
2. Render will automatically build and deploy your application
3. Wait for the build to complete (usually 2-5 minutes)

### 6. Verify Deployment

Once deployed, you can test your application:

1. **Health Check**: Visit `https://your-app-name.onrender.com/health`
2. **Landing Page**: Visit `https://your-app-name.onrender.com/`
3. **API Endpoints**: Test various endpoints like `/gk/health`, `/lexa/health`

## Testing Your Deployment

You can use the included test script:

```bash
# Set your deployed URL
export TEST_BASE_URL="https://your-app-name.onrender.com"

# Run the test
python test_deployment.py
```

## Troubleshooting

### Common Issues

1. **Build Fails**
   - Check that all dependencies are in `requirements.txt`
   - Verify Python version in `runtime.txt`
   - Check build logs in Render dashboard

2. **Application Crashes**
   - Check application logs in Render dashboard
   - Verify environment variables are set correctly
   - Ensure GROQ_API_KEY is valid

3. **API Calls Fail**
   - Check CORS configuration
   - Verify API endpoints are working
   - Test with the health check endpoint

4. **Static Files Not Loading**
   - Ensure all HTML files are in the root directory
   - Check file permissions
   - Verify file paths in HTML files

### Debug Commands

```bash
# Test locally before deploying
python app.py

# Check if all dependencies are installed
pip install -r requirements.txt

# Test API endpoints locally
curl http://localhost:5000/health
```

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Your Groq API key for AI functionality |
| `PORT` | No | Port number (Render sets this automatically) |
| `FLASK_ENV` | No | Set to 'development' for debug mode |

## API Endpoints

Your deployed application will have these endpoints:

- `GET /` - Landing page
- `GET /health` - Health check
- `POST /gk/generate` - Generate GK content
- `POST /gk/assistant` - GK assistant chat
- `POST /lexa/chat` - Lexa chatbot
- `POST /qt/generate-question` - Generate QT questions
- `POST /generate-test` - Generate sectional tests
- `POST /api/generate-practice` - Generate practice questions

## Monitoring

- **Logs**: View real-time logs in Render dashboard
- **Metrics**: Monitor performance and usage
- **Health Checks**: Automatic health monitoring
- **Alerts**: Set up notifications for downtime

## Scaling

Render automatically scales your application based on traffic. You can also:

- Upgrade to paid plans for better performance
- Set up custom domains
- Configure auto-scaling rules

## Security

- Environment variables are encrypted
- HTTPS is enabled by default
- CORS is configured for web security
- API keys are kept secure

## Support

If you encounter issues:

1. Check Render documentation: https://render.com/docs
2. Review application logs in Render dashboard
3. Test locally to isolate issues
4. Contact Render support if needed

---

**Happy Deploying! 🚀** 