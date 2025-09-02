'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery } from 'react-query'
import axios from 'axios'
import { 
  CheckCircle, 
  XCircle, 
  Clock, 
  Loader2, 
  Phone, 
  Globe, 
  MapPin,
  Calendar,
  DollarSign,
  AlertCircle,
  ChevronDown,
  ChevronUp
} from 'lucide-react'

interface ResultsDisplayProps {
  jobId: string
}

interface JobStatus {
  job_id: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  venue_id?: string
  confidence_score?: number
  happy_hour_found?: boolean
  consensus_data?: any
  total_cost_cents?: number
  agents_completed?: string[]
  error_message?: string
}

export default function ResultsDisplay({ jobId }: ResultsDisplayProps) {
  const [expanded, setExpanded] = useState(false)
  
  const { data: jobStatus, isLoading, error } = useQuery<JobStatus>(
    ['job', jobId],
    async () => {
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/job/${jobId}`
      )
      return response.data
    },
    {
      refetchInterval: (data) => {
        // Poll every 2 seconds while pending/in_progress
        if (data?.status === 'pending' || data?.status === 'in_progress') {
          return 2000
        }
        return false
      },
    }
  )

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    )
  }

  if (error || !jobStatus) {
    return (
      <div className="glass-card rounded-xl p-6 border-l-4 border-red-500">
        <div className="flex items-center gap-3">
          <XCircle className="w-6 h-6 text-red-500" />
          <p className="text-gray-700">Failed to load job status</p>
        </div>
      </div>
    )
  }

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'confidence-high'
    if (score >= 0.6) return 'confidence-medium'
    return 'confidence-low'
  }

  const getConfidenceLabel = (score: number) => {
    if (score >= 0.8) return 'High Confidence'
    if (score >= 0.6) return 'Medium Confidence'
    return 'Low Confidence'
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card rounded-2xl overflow-hidden"
    >
      {/* Status Header */}
      <div className={`p-6 ${
        jobStatus.status === 'completed' ? 'bg-gradient-to-r from-green-50 to-emerald-50' :
        jobStatus.status === 'failed' ? 'bg-gradient-to-r from-red-50 to-pink-50' :
        'bg-gradient-to-r from-blue-50 to-indigo-50'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {jobStatus.status === 'completed' ? (
              <CheckCircle className="w-8 h-8 text-green-600" />
            ) : jobStatus.status === 'failed' ? (
              <XCircle className="w-8 h-8 text-red-600" />
            ) : jobStatus.status === 'in_progress' ? (
              <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
            ) : (
              <Clock className="w-8 h-8 text-gray-600" />
            )}
            
            <div>
              <h3 className="text-xl font-bold text-gray-900">
                {jobStatus.status === 'completed' ? 'Analysis Complete' :
                 jobStatus.status === 'failed' ? 'Analysis Failed' :
                 jobStatus.status === 'in_progress' ? 'Analyzing...' :
                 'Queued'}
              </h3>
              <p className="text-sm text-gray-600">
                Job ID: {jobId.slice(0, 8)}...
              </p>
            </div>
          </div>

          {jobStatus.confidence_score !== undefined && (
            <div className={`w-20 h-20 confidence-ring ${getConfidenceColor(jobStatus.confidence_score)}`}>
              {Math.round(jobStatus.confidence_score * 100)}%
            </div>
          )}
        </div>
      </div>

      {/* Main Results */}
      {jobStatus.status === 'completed' && jobStatus.consensus_data && (
        <div className="p-6 space-y-6">
          {/* Happy Hour Found */}
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <span className="font-medium text-gray-700">Happy Hour Found:</span>
            <span className={`font-bold text-lg ${
              jobStatus.happy_hour_found ? 'text-green-600' : 'text-gray-400'
            }`}>
              {jobStatus.happy_hour_found ? 'YES' : 'NO'}
            </span>
          </div>

          {/* Schedule */}
          {jobStatus.consensus_data.schedule && (
            <div className="space-y-3">
              <h4 className="font-semibold text-gray-900 flex items-center gap-2">
                <Calendar className="w-5 h-5 text-primary-500" />
                Schedule
              </h4>
              <div className="bg-blue-50 rounded-lg p-4">
                <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                  {JSON.stringify(jobStatus.consensus_data.schedule, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Specials */}
          {jobStatus.consensus_data.specials && (
            <div className="space-y-3">
              <h4 className="font-semibold text-gray-900 flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-primary-500" />
                Specials
              </h4>
              <div className="bg-green-50 rounded-lg p-4">
                <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                  {JSON.stringify(jobStatus.consensus_data.specials, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Agents Used */}
          {jobStatus.agents_completed && (
            <div className="space-y-3">
              <h4 className="font-semibold text-gray-900">Verification Sources</h4>
              <div className="flex flex-wrap gap-2">
                {jobStatus.agents_completed.map((agent) => (
                  <span
                    key={agent}
                    className="px-3 py-1 bg-primary-100 text-primary-700 rounded-full text-sm font-medium"
                  >
                    {agent.replace('_', ' ').toUpperCase()}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Evidence Details */}
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <span className="font-medium text-gray-700">View Evidence Details</span>
            {expanded ? (
              <ChevronUp className="w-5 h-5 text-gray-500" />
            ) : (
              <ChevronDown className="w-5 h-5 text-gray-500" />
            )}
          </button>

          <AnimatePresence>
            {expanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="overflow-hidden"
              >
                <div className="bg-gray-50 rounded-lg p-4">
                  <pre className="text-xs text-gray-600 overflow-auto">
                    {JSON.stringify(jobStatus.consensus_data, null, 2)}
                  </pre>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Cost */}
          {jobStatus.total_cost_cents !== undefined && (
            <div className="flex items-center justify-between p-4 bg-yellow-50 rounded-lg">
              <span className="font-medium text-gray-700">Analysis Cost:</span>
              <span className="font-bold text-gray-900">
                ${(jobStatus.total_cost_cents / 100).toFixed(2)}
              </span>
            </div>
          )}
        </div>
      )}

      {/* In Progress Status */}
      {jobStatus.status === 'in_progress' && (
        <div className="p-6">
          <div className="flex items-center gap-3 text-blue-600">
            <Loader2 className="w-5 h-5 animate-spin" />
            <p>Analyzing restaurant data across multiple sources...</p>
          </div>
          
          {jobStatus.agents_completed && jobStatus.agents_completed.length > 0 && (
            <div className="mt-4">
              <p className="text-sm text-gray-600 mb-2">Completed agents:</p>
              <div className="flex flex-wrap gap-2">
                {jobStatus.agents_completed.map((agent) => (
                  <span
                    key={agent}
                    className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs"
                  >
                    {agent}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error State */}
      {jobStatus.status === 'failed' && (
        <div className="p-6">
          <div className="flex items-start gap-3 text-red-600">
            <AlertCircle className="w-5 h-5 mt-0.5" />
            <div>
              <p className="font-medium">Analysis failed</p>
              <p className="text-sm text-gray-600 mt-1">
                {jobStatus.error_message || 'An unexpected error occurred'}
              </p>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  )
}