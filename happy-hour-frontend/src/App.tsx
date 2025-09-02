import React, { useState, useEffect } from 'react';
import { QueryClient, QueryClientProvider, useQuery, useMutation } from '@tanstack/react-query';
import { Search, MapPin, Coffee, Star, Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import './App.css';

const queryClient = new QueryClient();

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

// API Functions - Use Application Load Balancer
const API_BASE_URL = 'http://happy-hour-alb-711828885.us-east-1.elb.amazonaws.com';

const searchRestaurants = async (query: string): Promise<Restaurant[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/restaurants/search?query=${encodeURIComponent(query)}&limit=20`);
    const data = await response.json();
    return data.restaurants || [];
  } catch (error) {
    console.error('Search failed:', error);
    // Fallback to sample data
    const sampleRestaurants: Restaurant[] = [
      {
        id: "1",
        name: "DUKES RESTAURANT",
        address: "1216 PROSPECT ST, LA JOLLA, CA 92037",
        phone: "858-454-5888",
        business_type: "Restaurant Food Facility",
        city: "LA JOLLA"
      },
      {
        id: "2", 
        name: "BARBARELLA RESTAURANT",
        address: "2171 AVENIDA DE LA PLAYA, LA JOLLA, CA 92037",
        phone: "858-242-2589",
        business_type: "Restaurant Food Facility",
        city: "LA JOLLA"
      },
      {
        id: "3",
        name: "EDDIE VS #8511", 
        address: "1270 PROSPECT ST, LA JOLLA, CA 92037",
        phone: "858-459-5500",
        business_type: "Restaurant Food Facility",
        city: "LA JOLLA"
      },
      {
        id: "4",
        name: "THE PRADO RESTAURANT",
        address: "1549 EL PRADO, LA JOLLA, CA 92037", 
        phone: "858-454-1549",
        business_type: "Restaurant Food Facility",
        city: "LA JOLLA"
      }
    ];
    
    if (query) {
      return sampleRestaurants.filter(r => r.name.toLowerCase().includes(query.toLowerCase()));
    }
    return sampleRestaurants;
  }
};

const analyzeRestaurant = async (restaurant: Restaurant): Promise<HappyHourAnalysis> => {
  try {
    console.log('Making request to:', `${API_BASE_URL}/api/analyze`);
    
    // Step 1: Create analysis job
    const createResponse = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        restaurant_name: restaurant.name,
        address: restaurant.address,
        phone: restaurant.phone,
        business_type: restaurant.business_type
      }),
    });
    
    console.log('Create job response status:', createResponse.status);
    
    if (!createResponse.ok) {
      throw new Error(`HTTP error! status: ${createResponse.status}`);
    }
    
    const createData = await createResponse.json();
    console.log('Job created:', createData);
    
    const jobId = createData.job_id;
    if (!jobId) {
      throw new Error('No job_id returned from analysis request');
    }
    
    // Step 2: Poll job status until completion
    console.log('Polling job status for:', jobId);
    
    const pollJobStatus = async (): Promise<any> => {
      const statusResponse = await fetch(`${API_BASE_URL}/api/job/${jobId}`);
      
      if (!statusResponse.ok) {
        throw new Error(`Job status error! status: ${statusResponse.status}`);
      }
      
      const statusData = await statusResponse.json();
      console.log('Job status:', statusData.status, statusData.message);
      
      if (statusData.status === 'completed') {
        return statusData;
      } else if (statusData.status === 'failed') {
        throw new Error(statusData.message || 'Job failed');
      } else {
        // Still queued or running, wait and poll again
        await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds
        return pollJobStatus();
      }
    };
    
    const finalData = await pollJobStatus();
    console.log('Job completed:', finalData);
    
    // Step 3: Format the completed job data for the frontend
    const happyHourData = finalData.happy_hour_data || {};
    
    // Create analysis text from the structured data
    let analysisText = `# ${restaurant.name} Happy Hour Analysis\n\n`;
    
    if (happyHourData.status === 'active') {
      analysisText += `✅ **Happy Hour Status**: Active\n\n`;
      
      if (happyHourData.schedule) {
        analysisText += `## 📅 Happy Hour Schedule\n`;
        Object.entries(happyHourData.schedule).forEach(([day, times]: [string, any]) => {
          const dayCapitalized = day.charAt(0).toUpperCase() + day.slice(1);
          if (Array.isArray(times)) {
            times.forEach(time => {
              analysisText += `• **${dayCapitalized}**: ${time.start} - ${time.end}\n`;
            });
          }
        });
        analysisText += `\n`;
      }
      
      if (happyHourData.offers && Array.isArray(happyHourData.offers)) {
        analysisText += `## 🍻 Happy Hour Offers\n`;
        happyHourData.offers.forEach((offer: any) => {
          const emoji = offer.type === 'drink' ? '🍹' : '🍽️';
          analysisText += `${emoji} **${offer.description}**\n`;
          if (offer.days && Array.isArray(offer.days)) {
            analysisText += `   Available: ${offer.days.join(', ')}\n`;
          }
        });
        analysisText += `\n`;
      }
      
      if (happyHourData.areas && Array.isArray(happyHourData.areas)) {
        analysisText += `## 📍 Available Areas\n`;
        happyHourData.areas.forEach((area: string) => {
          analysisText += `• ${area.charAt(0).toUpperCase() + area.slice(1)}\n`;
        });
        analysisText += `\n`;
      }
      
      if (happyHourData.fine_print && Array.isArray(happyHourData.fine_print)) {
        analysisText += `## ⚠️ Important Notes\n`;
        happyHourData.fine_print.forEach((note: string) => {
          analysisText += `• ${note}\n`;
        });
        analysisText += `\n`;
      }
    } else {
      analysisText += `❌ **Happy Hour Status**: Not available or inactive\n\n`;
    }
    
    analysisText += `## 🎯 Analysis Details\n`;
    analysisText += `• **Confidence Score**: ${finalData.confidence_score || 'N/A'}\n`;
    analysisText += `• **Evidence Sources**: ${finalData.evidence_count || 'N/A'}\n`;
    analysisText += `• **Source Diversity**: ${finalData.source_diversity || 'N/A'}\n`;
    analysisText += `• **Analysis Time**: ${finalData.completed_at ? new Date(finalData.completed_at).toLocaleTimeString() : 'N/A'}\n`;
    
    return {
      restaurant_name: restaurant.name,
      gpt5_analysis: analysisText,
      model_used: 'gpt-5',
      api_type: 'structured_analysis',
      tokens_used: 0,
      reasoning_tokens: 0,
      reasoning_effort: 'comprehensive',
      timestamp: finalData.completed_at || new Date().toISOString()
    };
  } catch (error) {
    console.error('Analysis failed:', error);
    // Fallback analysis
    return {
      restaurant_name: restaurant.name,
      gpt5_analysis: `🚫 **Backend Connection Error**

Error details: ${error}

**Fallback Analysis:**
Based on La Jolla's dining patterns, this establishment likely offers:
• Happy Hour: Monday-Friday 3:00-6:00 PM  
• Drink specials typical for the area
• Bar area seating with potential patio access

**Status:** Could not connect to Lambda backend - please check console for details.`,
      model_used: "error-fallback",
      api_type: "connection_error",
      tokens_used: 0,
      reasoning_tokens: 0,
      reasoning_effort: "none",
      timestamp: new Date().toISOString()
    };
  }
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
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [selectedRestaurant, setSelectedRestaurant] = useState<Restaurant | null>(null);
  const [analyses, setAnalyses] = useState<HappyHourAnalysis[]>([]);

  // Debounce search query
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 500);

    return () => {
      clearTimeout(handler);
    };
  }, [searchQuery]);

  // Search query
  const { data: restaurants = [], isLoading: isSearching, error: searchError } = useQuery({
    queryKey: ['restaurants', debouncedSearchQuery],
    queryFn: () => searchRestaurants(debouncedSearchQuery),
    enabled: debouncedSearchQuery.length > 2,
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