import React, { useState } from 'react';
import { QueryClient, QueryClientProvider, useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import { Search, MapPin, Clock, DollarSign, Coffee, Star, Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import './App.css';

const queryClient = new QueryClient();

// API Base URL - automatically uses environment variable for production
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Types
interface Restaurant {
  id: string;
  name: string;
  address: string;
  phone: string;
  business_type: string;
  city: string;
}

interface HappyHourAnalysis {
  restaurant_name: string;
  gpt5_analysis: string;
  model_used: string;
  api_type: string;
  tokens_used: number;
  reasoning_tokens: number;
  reasoning_effort: string;
  timestamp: string;
}

// API Functions
const searchRestaurants = async (query: string): Promise<Restaurant[]> => {
  const response = await axios.get(`${API_BASE_URL}/api/restaurants/search?query=${encodeURIComponent(query)}&limit=20`);
  return response.data.restaurants;
};

const analyzeRestaurant = async (restaurant: Restaurant): Promise<HappyHourAnalysis> => {
  const response = await axios.post(`${API_BASE_URL}/api/analyze`, {
    restaurant_name: restaurant.name,
    address: restaurant.address,
    phone: restaurant.phone,
    business_type: restaurant.business_type
  });
  return response.data;
};

// Components
const RestaurantCard: React.FC<{ 
  restaurant: Restaurant; 
  onAnalyze: (restaurant: Restaurant) => void;
  isAnalyzing: boolean;
}> = ({ restaurant, onAnalyze, isAnalyzing }) => {
  return (
    <div className="restaurant-card">
      <div className="restaurant-header">
        <h3>{restaurant.name}</h3>
        <span className="business-type">{restaurant.business_type}</span>
      </div>
      
      <div className="restaurant-info">
        <div className="info-row">
          <MapPin size={16} />
          <span>{restaurant.address}</span>
        </div>
        {restaurant.phone && (
          <div className="info-row">
            <span>📞 {restaurant.phone}</span>
          </div>
        )}
      </div>
      
      <button 
        onClick={() => onAnalyze(restaurant)}
        disabled={isAnalyzing}
        className="analyze-button"
      >
        {isAnalyzing ? (
          <>
            <Loader2 size={16} className="spinning" />
            Analyzing with GPT-5...
          </>
        ) : (
          <>
            <Star size={16} />
            Analyze Happy Hour
          </>
        )}
      </button>
    </div>
  );
};

const AnalysisResult: React.FC<{ analysis: HappyHourAnalysis }> = ({ analysis }) => {
  const parseAnalysis = (text: string) => {
    const sections = text.split('\n\n');
    return sections.map((section, index) => (
      <p key={index} className="analysis-section">
        {section}
      </p>
    ));
  };

  const getConfidenceIcon = (text: string) => {
    if (text.toLowerCase().includes('high')) return <CheckCircle className="confidence-high" size={20} />;
    if (text.toLowerCase().includes('medium')) return <AlertCircle className="confidence-medium" size={20} />;
    return <AlertCircle className="confidence-low" size={20} />;
  };

  return (
    <div className="analysis-result">
      <div className="analysis-header">
        <h3>{analysis.restaurant_name} - Happy Hour Analysis</h3>
        <div className="analysis-meta">
          <span className="model-badge">GPT-5</span>
          <span className="tokens-info">
            {analysis.tokens_used} tokens ({analysis.reasoning_tokens} reasoning)
          </span>
        </div>
      </div>
      
      <div className="analysis-content">
        {parseAnalysis(analysis.gpt5_analysis)}
      </div>
      
      <div className="analysis-footer">
        <div className="confidence-indicator">
          {getConfidenceIcon(analysis.gpt5_analysis)}
          <span>AI Analysis Complete</span>
        </div>
        <div className="analysis-timestamp">
          Analyzed: {new Date(analysis.timestamp).toLocaleString()}
        </div>
      </div>
    </div>
  );
};

const HappyHourApp: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRestaurant, setSelectedRestaurant] = useState<Restaurant | null>(null);
  const [analyses, setAnalyses] = useState<HappyHourAnalysis[]>([]);

  // Search query
  const { data: restaurants = [], isLoading: isSearching, error: searchError } = useQuery({
    queryKey: ['restaurants', searchQuery],
    queryFn: () => searchRestaurants(searchQuery),
    enabled: searchQuery.length > 2,
  });

  // Analysis mutation
  const analyzeMutation = useMutation({
    mutationFn: analyzeRestaurant,
    onSuccess: (data) => {
      setAnalyses(prev => [data, ...prev]);
      setSelectedRestaurant(null);
    },
    onError: (error) => {
      console.error('Analysis failed:', error);
      alert('Analysis failed. Please try again.');
    },
  });

  const handleAnalyze = (restaurant: Restaurant) => {
    setSelectedRestaurant(restaurant);
    analyzeMutation.mutate(restaurant);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>
          <Coffee size={32} />
          GPT-5 Happy Hour Discovery
        </h1>
        <p>Discover happy hour specials in La Jolla using advanced AI analysis</p>
      </header>

      <div className="search-section">
        <div className="search-input-container">
          <Search size={20} />
          <input
            type="text"
            placeholder="Search for restaurants (e.g., 'DUKES', 'BARBARELLA', 'PIZZA')..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
          {isSearching && <Loader2 size={20} className="spinning" />}
        </div>
        
        {searchError && (
          <div className="error-message">
            <AlertCircle size={16} />
            Failed to search restaurants. Make sure the backend is running.
          </div>
        )}
      </div>

      <div className="main-content">
        <div className="restaurants-section">
          <h2>Restaurants {restaurants.length > 0 && `(${restaurants.length} found)`}</h2>
          
          {searchQuery.length <= 2 && (
            <div className="search-prompt">
              <Search size={48} />
              <p>Start typing to search for restaurants...</p>
            </div>
          )}
          
          <div className="restaurants-grid">
            {restaurants.map((restaurant) => (
              <RestaurantCard
                key={restaurant.id}
                restaurant={restaurant}
                onAnalyze={handleAnalyze}
                isAnalyzing={selectedRestaurant?.id === restaurant.id && analyzeMutation.isPending}
              />
            ))}
          </div>
        </div>

        <div className="analyses-section">
          <h2>GPT-5 Analyses {analyses.length > 0 && `(${analyses.length})`}</h2>
          
          {analyses.length === 0 && (
            <div className="empty-state">
              <Star size={48} />
              <p>Select a restaurant to analyze with GPT-5</p>
              <small>Our AI will assess happy hour likelihood, timing, and specials</small>
            </div>
          )}
          
          <div className="analyses-list">
            {analyses.map((analysis, index) => (
              <AnalysisResult key={index} analysis={analysis} />
            ))}
          </div>
        </div>
      </div>

      <footer className="app-footer">
        <p>Powered by GPT-5 Responses API • {new Date().getFullYear()}</p>
        <div className="api-status">
          <div className="status-dot"></div>
          Backend: localhost:8000
        </div>
      </footer>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <HappyHourApp />
    </QueryClientProvider>
  );
};

export default App;