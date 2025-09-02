'use client'

import { useQuery } from 'react-query'
import axios from 'axios'
import { TrendingUp, Building2, CheckCircle, Sparkles } from 'lucide-react'
import { motion } from 'framer-motion'

interface Stats {
  total_venues: number
  total_jobs: number
  happy_hours_found: number
  gpt5_enabled: boolean
}

export default function StatsBar() {
  const { data: stats, isLoading } = useQuery<Stats>(
    'stats',
    async () => {
      const response = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/stats`)
      return response.data
    },
    {
      refetchInterval: 30000, // Refresh every 30 seconds
    }
  )

  if (isLoading || !stats) {
    return null
  }

  const statItems = [
    {
      icon: Building2,
      label: 'Venues Analyzed',
      value: stats.total_venues.toLocaleString(),
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
    },
    {
      icon: TrendingUp,
      label: 'Total Analyses',
      value: stats.total_jobs.toLocaleString(),
      color: 'text-green-600',
      bgColor: 'bg-green-100',
    },
    {
      icon: CheckCircle,
      label: 'Happy Hours Found',
      value: stats.happy_hours_found.toLocaleString(),
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
    },
    {
      icon: Sparkles,
      label: 'AI Model',
      value: 'GPT-5',
      color: 'text-primary-600',
      bgColor: 'bg-primary-100',
    },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-8"
    >
      <div className="glass-card rounded-xl p-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {statItems.map((item, index) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.1 }}
              className="flex items-center gap-3"
            >
              <div className={`w-10 h-10 ${item.bgColor} rounded-lg flex items-center justify-center`}>
                <item.icon className={`w-5 h-5 ${item.color}`} />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{item.value}</p>
                <p className="text-xs text-gray-600">{item.label}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  )
}