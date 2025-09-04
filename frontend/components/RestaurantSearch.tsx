'use client'

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, MapPin, Phone, Globe, Loader2, ChevronDown } from 'lucide-react'
import axios from 'axios'
import toast from 'react-hot-toast'

interface RestaurantSearchProps {
  onJobCreated: (jobId: string) => void
}

interface Restaurant {
  id: string
  name: string
  address: string
  phone?: string
  city: string
  state: string
}

export default function RestaurantSearch({ onJobCreated }: RestaurantSearchProps) {
  const [formData, setFormData] = useState({
    name: '',
    address: '',
    phone: '',
    website: '',
    skipVoiceVerify: false,
  })
  const [isLoading, setIsLoading] = useState(false)
  const [searchResults, setSearchResults] = useState<Restaurant[]>([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [isSearching, setIsSearching] = useState(false)
  const searchRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Search restaurants as user types
  useEffect(() => {
    const searchRestaurants = async () => {
      if (formData.name.length < 2) {
        setSearchResults([])
        setShowDropdown(false)
        return
      }

      setIsSearching(true)
      try {
        const response = await axios.get(
          `${process.env.NEXT_PUBLIC_API_URL}/api/restaurants/search?query=${encodeURIComponent(formData.name)}&limit=10`
        )
        setSearchResults(response.data.restaurants || [])
        setShowDropdown(true)
      } catch (error) {
        console.error('Search error:', error)
        setSearchResults([])
      } finally {
        setIsSearching(false)
      }
    }

    const timeoutId = setTimeout(searchRestaurants, 300) // Debounce
    return () => clearTimeout(timeoutId)
  }, [formData.name])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowDropdown(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const selectRestaurant = (restaurant: Restaurant) => {
    setFormData({
      ...formData,
      name: restaurant.name,
      address: restaurant.address,
      phone: restaurant.phone || '',
    })
    setShowDropdown(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.name) {
      toast.error('Restaurant name is required')
      return
    }

    setIsLoading(true)
    
    try {
      // Enhanced payload with location context for better matching
      const payload = {
        restaurant_name: formData.name,
        address: formData.address || undefined,
        phone: formData.phone || undefined,
        website: formData.website || undefined,
        skip_voice_verify: formData.skipVoiceVerify,
        priority: 'normal',
        // Add source context for future Google Places integration
        source: 'manual_entry',
        location_context: formData.address ? {
          full_address: formData.address
        } : undefined
      }
      
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/analyze`,
        payload
      )

      const { job_id, message } = response.data
      
      toast.success(message || 'Analysis started!')
      onJobCreated(job_id)
      
      // Clear form
      setFormData({
        name: '',
        address: '',
        phone: '',
        website: '',
        skipVoiceVerify: false,
      })
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to start analysis')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card rounded-2xl p-8"
      >
        <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
          <Search className="w-6 h-6 text-primary-500" />
          Search for Happy Hour
        </h2>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Restaurant Name with Autocomplete */}
          <div ref={searchRef} className="relative">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Restaurant Name *
            </label>
            <div className="relative">
              <input
                ref={inputRef}
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Start typing restaurant name (fuzzy matching supported)..."
                className="w-full px-4 py-3 pr-10 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                disabled={isLoading}
                autoComplete="off"
              />
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                {isSearching ? (
                  <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                ) : (
                  <Search className="w-4 h-4 text-gray-400" />
                )}
              </div>
            </div>
            
            {/* Search Dropdown */}
            <AnimatePresence>
              {showDropdown && searchResults.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto"
                >
                  {searchResults.map((restaurant) => (
                    <button
                      key={restaurant.id}
                      type="button"
                      onClick={() => selectRestaurant(restaurant)}
                      className="w-full px-4 py-3 text-left hover:bg-gray-50 focus:bg-gray-50 focus:outline-none border-b border-gray-100 last:border-b-0"
                    >
                      <div className="font-medium text-gray-900">{restaurant.name}</div>
                      <div className="text-sm text-gray-500 flex items-center gap-1">
                        <MapPin className="w-3 h-3" />
                        {restaurant.address}
                      </div>
                      <div className="text-xs text-gray-400">
                        {restaurant.city}, {restaurant.state}
                      </div>
                    </button>
                  ))}
                  
                  {searchResults.length === 0 && formData.name.length >= 2 && !isSearching && (
                    <div className="px-4 py-3 text-gray-500 text-sm">
                      No restaurants found. You can still manually enter details.
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Address */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <MapPin className="w-4 h-4 inline mr-1" />
              Address
            </label>
            <input
              type="text"
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              placeholder="e.g., 1216 Prospect St, La Jolla, CA 92037"
              className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
              disabled={isLoading}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Phone */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Phone className="w-4 h-4 inline mr-1" />
                Phone Number
              </label>
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="e.g., (858) 454-5325"
                className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                disabled={isLoading}
              />
            </div>

            {/* Website */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Globe className="w-4 h-4 inline mr-1" />
                Website
              </label>
              <input
                type="url"
                value={formData.website}
                onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                placeholder="e.g., https://dukeslajolla.com"
                className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                disabled={isLoading}
              />
            </div>
          </div>

          {/* Options */}
          <div className="bg-gray-50 rounded-lg p-4 space-y-3">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.skipVoiceVerify}
                onChange={(e) => setFormData({ ...formData, skipVoiceVerify: e.target.checked })}
                className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                disabled={isLoading}
              />
              <span className="text-sm text-gray-700">
                Skip phone verification (faster but less accurate)
              </span>
            </label>
            
            <div className="text-xs text-gray-600">
              <div className="font-medium mb-1">🎯 Smart Matching:</div>
              <ul className="space-y-1 pl-2">
                <li>• Supports partial names (e.g., "Pizza" finds "House of Pizza")</li>
                <li>• Handles business suffixes (e.g., "Mario's Restaurant" → "Mario's")</li>
                <li>• Works with Google Places names</li>
              </ul>
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading || !formData.name}
            className="w-full btn-primary flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Search className="w-5 h-5" />
                Find Happy Hour
              </>
            )}
          </button>
        </form>
      </motion.div>
    </div>
  )
}