# GPT-5 Happy Hour Discovery System

A modern web application that uses OpenAI's GPT-5 to intelligently analyze restaurants and predict their happy hour offerings.

## 🚀 Live Demo

- **Frontend**: [Deployed on Vercel](https://your-frontend-url.vercel.app)
- **Backend API**: [Deployed on Vercel](https://your-backend-url.vercel.app)

## ✨ Features

- **GPT-5 Powered Analysis**: Uses OpenAI's latest GPT-5 model with Responses API
- **Intelligent Reasoning**: Leverages GPT-5's reasoning tokens for deep analysis
- **Real-time Search**: Search through La Jolla restaurants instantly
- **Beautiful UI**: Modern React interface with responsive design
- **Confidence Scoring**: AI provides confidence levels for each analysis
- **Source Tracking**: Complete audit trail of AI reasoning process

## 🏗️ Architecture

### Backend
- **FastAPI** with async support
- **GPT-5 Responses API** integration
- **Pydantic** models for type safety
- **Vercel** serverless deployment

### Frontend
- **React 19** with TypeScript
- **TanStack Query** for data fetching
- **Lucide React** icons
- **CSS Grid** responsive layout

## 📊 GPT-5 Features Used

- **Responses API**: Official GPT-5 interface (not Chat Completions)
- **Reasoning Tokens**: Deep thinking process with 1000+ reasoning tokens
- **Structured Outputs**: Deterministic JSON responses
- **Medium Reasoning Effort**: Balanced analysis depth
- **Token Tracking**: Complete usage monitoring

## 🚀 Quick Deploy

### 1. Backend Deployment

```bash
# In the hhmap directory
npx vercel

# Set environment variables in Vercel dashboard:
# OPENAI_API_KEY = your-gpt5-api-key
```

### 2. Frontend Deployment

```bash
# In the happy-hour-frontend directory
npx vercel

# Set environment variables in Vercel dashboard:
# REACT_APP_API_URL = your-backend-vercel-url
```

## 🔧 Local Development

### Prerequisites
- Python 3.9+
- Node.js 18+
- OpenAI API key with GPT-5 access

### Backend Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file
echo "OPENAI_API_KEY=your-key-here" > .env

# Run backend
python3 api/index.py
```

### Frontend Setup
```bash
cd happy-hour-frontend
npm install
npm start
```

## 📁 Project Structure

```
hhmap/
├── api/
│   └── index.py                 # Vercel-optimized FastAPI backend
├── happy-hour-frontend/         # React TypeScript app
│   ├── src/
│   │   ├── App.tsx              # Main React component
│   │   └── App.css              # Modern styling
│   ├── package.json
│   └── vercel.json              # Frontend deployment config
├── food_permits_restaurants.csv # Restaurant data
├── proper_gpt5_system.py        # GPT-5 integration logic
├── requirements.txt             # Python dependencies
├── vercel.json                  # Backend deployment config
└── README.md
```

## 🧠 How It Works

1. **Search**: User types restaurant name in React frontend
2. **Query**: Frontend calls FastAPI backend with search terms
3. **Analyze**: User clicks "Analyze Happy Hour" button
4. **GPT-5**: Backend sends structured prompt to GPT-5 Responses API
5. **Reasoning**: GPT-5 uses 1000+ reasoning tokens to analyze
6. **Results**: Structured response with confidence scores and timing
7. **Display**: Frontend shows beautiful analysis with token usage

## 🎯 Sample Analysis

GPT-5 provides detailed assessments like:

```
Assessment for: DUKES RESTAURANT, 1216 Prospect St, La Jolla, CA 92037

1) Likelihood of having happy hour: High

2) Restaurant category: Upscale-casual, full-service restaurant with 
   full bar (ocean-view, Hawaiian/seafood concept)

3) Estimated happy hour schedule:
   - Days: Monday–Friday
   - Time: 3:00–6:00 PM  
   - Area: Bar/lounge and patio seating

4) Typical specials:
   - Drinks: Discounted draft beer, house wines, mai tai cocktails
   - Food: Poke, coconut shrimp, sliders ($8-15 range)

5) Confidence level: 80%
```

## 💰 Costs

Using GPT-5 at $1.25/1M input tokens and $10/1M output tokens:
- Average analysis: ~1,800 total tokens
- Cost per analysis: ~$0.02
- Very affordable for comprehensive AI analysis

## 🛠️ Environment Variables

### Backend (`vercel.com` dashboard)
- `OPENAI_API_KEY`: Your OpenAI API key with GPT-5 access

### Frontend (`vercel.com` dashboard)  
- `REACT_APP_API_URL`: Your backend Vercel URL

## 📈 Monitoring

- **Token Usage**: Tracked per request
- **Reasoning Tokens**: Shows GPT-5's thinking process  
- **Confidence Scores**: AI self-assessment of analysis quality
- **Response Times**: Backend performance monitoring

## 🔗 API Endpoints

- `GET /api/restaurants/search` - Search restaurants
- `POST /api/analyze` - Analyze restaurant with GPT-5
- `GET /api/stats` - System statistics
- `GET /health` - Health check

## 🚦 Status

- ✅ GPT-5 Responses API integration
- ✅ React frontend with TypeScript
- ✅ Vercel deployment ready
- ✅ Responsive design
- ✅ Error handling & loading states
- ✅ Token usage tracking

Built with ❤️ using GPT-5's advanced reasoning capabilities.