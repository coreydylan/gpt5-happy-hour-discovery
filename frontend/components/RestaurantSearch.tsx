'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Search, MapPin, Phone, Globe, Loader2 } from 'lucide-react'
import axios from 'axios'
import toast from 'react-hot-toast'

interface RestaurantSearchProps {
  onJobCreated: (jobId: string) => void
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.name) {
      toast.error('Restaurant name is required')
      return
    }

    setIsLoading(true)
    
    try {
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/analyze`,
        {
          name: formData.name,
          address: formData.address || undefined,
          phone: formData.phone || undefined,
          website: formData.website || undefined,
          skip_voice_verify: formData.skipVoiceVerify,
          priority: 'normal'
        }
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
          {/* Restaurant Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Restaurant Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., Duke's La Jolla"
              className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
              disabled={isLoading}
            />
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
          <div className="bg-gray-50 rounded-lg p-4">
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