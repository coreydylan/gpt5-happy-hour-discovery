# GPT-5 Happy Hour Discovery - Git & Vercel Deployment

## 🚀 Quick Deployment Guide

### 1. Initialize Git Repository
```bash
# In the hhmap directory
git init
git add .
git commit -m "Initial commit: GPT-5 Happy Hour Discovery System"

# Connect to GitHub (create repo first on GitHub.com)
git remote add origin https://github.com/YOUR_USERNAME/gpt5-happy-hour-discovery.git
git branch -M main
git push -u origin main
```

### 2. Deploy Backend to Vercel
```bash
cd hhmap
npx vercel

# Follow prompts:
# - Link to existing project? N
# - Project name: gpt5-happy-hour-api
# - Directory: ./
# - Override settings? N
```

### 3. Deploy Frontend to Vercel
```bash
cd happy-hour-frontend
npx vercel

# Follow prompts:
# - Link to existing project? N  
# - Project name: gpt5-happy-hour-frontend
# - Directory: ./
# - Override settings? Y
# - Build command: npm run build
# - Output directory: build
```

### 4. Environment Variables
After deployment, add these environment variables in Vercel dashboard:

**Backend (API):**
- `OPENAI_API_KEY` = your OpenAI API key

**Frontend:**
- `REACT_APP_API_URL` = your backend Vercel URL (e.g., https://gpt5-happy-hour-api.vercel.app)

### 5. Update Frontend API URL
The frontend will automatically use the environment variable for the API URL.

---

## 📁 Project Structure for Deployment

```
hhmap/
├── api/                          # Vercel API directory
│   └── index.py                  # Backend entry point
├── happy-hour-frontend/          # React app (separate Vercel project)
│   ├── src/
│   ├── package.json
│   └── vercel.json
├── food_permits_restaurants.csv  # Data file
├── proper_gpt5_system.py         # GPT-5 logic
├── requirements.txt              # Python dependencies
├── vercel.json                   # Backend config
└── README.md
```

---

## ⚙️ Configuration Files Created

The setup creates all necessary config files automatically for seamless deployment.