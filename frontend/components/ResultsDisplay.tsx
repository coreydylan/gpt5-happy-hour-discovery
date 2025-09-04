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
  ChevronUp,
  ExternalLink,
  Brain,
  Shield,
  RefreshCw
} from 'lucide-react'

interface ResultsDisplayProps {
  jobId: string
}

interface JobStatus {
  job_id: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  venue_id?: string
  confidence_score?: number
  happy_hour_data?: {
    status: 'active' | 'inactive'
    schedule: any
    offers: any[]
    areas: any[]
    fine_print: string[]
  }
  reasoning?: string
  sources?: Array<{
    url: string
    title: string
    type: string
  }>
  evidence_quality?: 'high' | 'medium' | 'low' | 'none'
  total_cost_cents?: number
  agents_completed?: string[]
  error_message?: string
}

export default function ResultsDisplay({ jobId }: ResultsDisplayProps) {
  const [expanded, setExpanded] = useState(false)
  const [debugInfo, setDebugInfo] = useState<string>('')
  
  const { data: jobStatus, isLoading, error, refetch } = useQuery<JobStatus>(
    ['job', jobId],
    async () => {
      try {
        // Try the provided job ID first
        setDebugInfo(`Trying job ID: ${jobId}`)
        const response = await axios.get(
          `${process.env.NEXT_PUBLIC_API_URL}/api/job/${jobId}`
        )
        setDebugInfo(`✅ Found job: ${jobId} - Status: ${response.data.status}`)
        return response.data
      } catch (error: any) {
        // If job ID has old format suffix, try without it
        if (jobId.endsWith('-uuid') && error.response?.status === 404) {
          const cleanJobId = jobId.replace('-uuid', '')
          setDebugInfo(`🔄 Trying clean ID: ${cleanJobId}`)
          const fallbackResponse = await axios.get(
            `${process.env.NEXT_PUBLIC_API_URL}/api/job/${cleanJobId}`
          )
          setDebugInfo(`✅ Found job: ${cleanJobId} - Status: ${fallbackResponse.data.status}`)
          return fallbackResponse.data
        }
        // If short ID, try with suffix for legacy jobs
        if (jobId.length <= 8 && error.response?.status === 404) {
          const legacyJobId = `${jobId}-uuid`
          setDebugInfo(`🔄 Trying legacy ID: ${legacyJobId}`)
          const legacyResponse = await axios.get(
            `${process.env.NEXT_PUBLIC_API_URL}/api/job/${legacyJobId}`
          )
          setDebugInfo(`✅ Found job: ${legacyJobId} - Status: ${legacyResponse.data.status}`)
          return legacyResponse.data
        }
        setDebugInfo(`❌ Job not found: ${jobId}`)
        throw error
      }
    },
    {
      refetchInterval: (data) => {
        // Poll every 2 seconds while pending/in_progress
        if (data?.status === 'pending' || data?.status === 'in_progress') {
          return 2000
        }
        return false
      },
      retry: (failureCount, error: any) => {
        // Don't retry if it's a 404 after our fallback attempts
        if (error?.response?.status === 404 && failureCount >= 1) {
          return false
        }
        return failureCount < 3
      }
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
              {debugInfo && (
                <p className="text-xs text-blue-600 mt-1">
                  {debugInfo}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => refetch()}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
              title="Refresh job status"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          {jobStatus.confidence_score !== undefined && (
            <div className={`w-20 h-20 confidence-ring ${getConfidenceColor(jobStatus.confidence_score)}`}>
              {Math.round(jobStatus.confidence_score * 100)}%
            </div>
          )}
        </div>
      </div>

      {/* Main Results */}
      {jobStatus.status === 'completed' && jobStatus.happy_hour_data && (
        <div className="p-6 space-y-6">
          {/* Happy Hour Status */}
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <span className="font-medium text-gray-700">Happy Hour Status:</span>
            <span className={`font-bold text-lg ${
              jobStatus.happy_hour_data.status === 'active' ? 'text-green-600' : 'text-gray-400'
            }`}>
              {jobStatus.happy_hour_data.status === 'active' ? 'ACTIVE' : 'INACTIVE'}
            </span>
          </div>

          {/* GPT-5 Reasoning */}
          {jobStatus.reasoning && (
            <div className="space-y-3">
              <h4 className="font-semibold text-gray-900 flex items-center gap-2">
                <Brain className="w-5 h-5 text-purple-500" />
                GPT-5 Analysis Reasoning
              </h4>
              <div className="bg-purple-50 rounded-lg p-4">
                <p className="text-sm text-gray-700 leading-relaxed">
                  {jobStatus.reasoning}
                </p>
              </div>
            </div>
          )}

          {/* Sources */}
          {jobStatus.sources && jobStatus.sources.length > 0 && (
            <div className="space-y-3">
              <h4 className="font-semibold text-gray-900 flex items-center gap-2">
                <ExternalLink className="w-5 h-5 text-blue-500" />
                Sources & Evidence
              </h4>
              <div className="space-y-2">
                {jobStatus.sources.map((source, index) => (
                  <div key={index} className="bg-blue-50 rounded-lg p-3 flex items-center justify-between">
                    <div>
                      <p className="font-medium text-blue-900">{source.title}</p>
                      <p className="text-xs text-blue-600 uppercase">{source.type}</p>
                    </div>
                    <a 
                      href={source.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-blue-500 hover:text-blue-700"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Evidence Quality */}
          {jobStatus.evidence_quality && (
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-gray-500" />
                <span className="font-medium text-gray-700">Evidence Quality:</span>
              </div>
              <span className={`font-bold text-sm uppercase px-3 py-1 rounded-full ${
                jobStatus.evidence_quality === 'high' ? 'bg-green-100 text-green-700' :
                jobStatus.evidence_quality === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                jobStatus.evidence_quality === 'low' ? 'bg-orange-100 text-orange-700' :
                'bg-gray-100 text-gray-700'
              }`}>
                {jobStatus.evidence_quality}
              </span>
            </div>
          )}

          {/* Schedule */}
          {jobStatus.happy_hour_data.schedule && Object.keys(jobStatus.happy_hour_data.schedule).length > 0 && (
            <div className="space-y-3">
              <h4 className="font-semibold text-gray-900 flex items-center gap-2">
                <Calendar className="w-5 h-5 text-primary-500" />
                Schedule
              </h4>
              <div className="bg-blue-50 rounded-lg p-4">
                <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                  {JSON.stringify(jobStatus.happy_hour_data.schedule, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Offers */}
          {jobStatus.happy_hour_data.offers && jobStatus.happy_hour_data.offers.length > 0 && (
            <div className="space-y-3">
              <h4 className="font-semibold text-gray-900 flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-primary-500" />
                Happy Hour Offers
              </h4>
              <div className="bg-green-50 rounded-lg p-4">
                <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                  {JSON.stringify(jobStatus.happy_hour_data.offers, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Fine Print */}
          {jobStatus.happy_hour_data.fine_print && jobStatus.happy_hour_data.fine_print.length > 0 && (
            <div className="space-y-3">
              <h4 className="font-semibold text-gray-900 flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-orange-500" />
                Important Notes
              </h4>
              <div className="bg-orange-50 rounded-lg p-4">
                <ul className="text-sm text-gray-700 space-y-1">
                  {jobStatus.happy_hour_data.fine_print.map((note, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="text-orange-500 mt-1">•</span>
                      <span>{note}</span>
                    </li>
                  ))}
                </ul>
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
                    {JSON.stringify(jobStatus.happy_hour_data, null, 2)}
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