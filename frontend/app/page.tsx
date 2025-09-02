'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Search, Upload, Sparkles, Phone, Globe, MapPin, Clock } from 'lucide-react'
import RestaurantSearch from '@/components/RestaurantSearch'
import BulkUpload from '@/components/BulkUpload'
import ResultsDisplay from '@/components/ResultsDisplay'
import StatsBar from '@/components/StatsBar'

export default function Home() {
  const [activeTab, setActiveTab] = useState<'search' | 'bulk'>('search')
  const [currentJob, setCurrentJob] = useState<string | null>(null)

  return (
    <main className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Header */}
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-12"
      >
        <div className="flex items-center justify-center mb-4">
          <Sparkles className="w-12 h-12 text-primary-500 mr-3" />
          <h1 className="text-5xl font-bold bg-gradient-to-r from-primary-600 to-primary-400 bg-clip-text text-transparent">
            Happy Hour Discovery
          </h1>
        </div>
        <p className="text-gray-600 text-lg">
          GPT-5 powered verification with phone calls, website scraping, and multi-source consensus
        </p>
        <div className="flex items-center justify-center gap-6 mt-4 text-sm text-gray-500">
          <span className="flex items-center gap-1">
            <Phone className="w-4 h-4" /> Direct calls to restaurants
          </span>
          <span className="flex items-center gap-1">
            <Globe className="w-4 h-4" /> Website & review analysis
          </span>
          <span className="flex items-center gap-1">
            <MapPin className="w-4 h-4" /> Multi-source verification
          </span>
        </div>
      </motion.div>

      {/* Stats Bar */}
      <StatsBar />

      {/* Tab Navigation */}
      <div className="flex justify-center mb-8">
        <div className="bg-white rounded-full shadow-lg p-1 flex">
          <button
            onClick={() => setActiveTab('search')}
            className={`px-6 py-3 rounded-full font-medium transition-all duration-200 flex items-center gap-2 ${
              activeTab === 'search'
                ? 'bg-primary-500 text-white'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Search className="w-4 h-4" />
            Single Search
          </button>
          <button
            onClick={() => setActiveTab('bulk')}
            className={`px-6 py-3 rounded-full font-medium transition-all duration-200 flex items-center gap-2 ${
              activeTab === 'bulk'
                ? 'bg-primary-500 text-white'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Upload className="w-4 h-4" />
            Bulk Upload
          </button>
        </div>
      </div>

      {/* Main Content */}
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, x: activeTab === 'search' ? -20 : 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3 }}
      >
        {activeTab === 'search' ? (
          <RestaurantSearch onJobCreated={setCurrentJob} />
        ) : (
          <BulkUpload />
        )}
      </motion.div>

      {/* Results Display */}
      {currentJob && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-12"
        >
          <ResultsDisplay jobId={currentJob} />
        </motion.div>
      )}

      {/* Feature Cards */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16"
      >
        <div className="glass-card rounded-xl p-6">
          <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
            <Phone className="w-6 h-6 text-green-600" />
          </div>
          <h3 className="text-lg font-semibold mb-2">Voice Verification</h3>
          <p className="text-gray-600 text-sm">
            We actually call restaurants to verify happy hour details directly with staff
          </p>
        </div>

        <div className="glass-card rounded-xl p-6">
          <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
            <Globe className="w-6 h-6 text-blue-600" />
          </div>
          <h3 className="text-lg font-semibold mb-2">Multi-Source Analysis</h3>
          <p className="text-gray-600 text-sm">
            Combines data from websites, Google, Yelp, and more for accurate information
          </p>
        </div>

        <div className="glass-card rounded-xl p-6">
          <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
            <Sparkles className="w-6 h-6 text-purple-600" />
          </div>
          <h3 className="text-lg font-semibold mb-2">GPT-5 Powered</h3>
          <p className="text-gray-600 text-sm">
            Uses GPT-5's reasoning capabilities for intelligent extraction and consensus
          </p>
        </div>
      </motion.div>
    </main>
  )
}