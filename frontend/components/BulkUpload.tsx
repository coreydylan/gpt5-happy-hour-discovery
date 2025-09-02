'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion } from 'framer-motion'
import { Upload, FileText, X, Loader2, Download } from 'lucide-react'
import Papa from 'papaparse'
import axios from 'axios'
import toast from 'react-hot-toast'

interface RestaurantRow {
  name: string
  address?: string
  phone?: string
  website?: string
}

export default function BulkUpload() {
  const [csvData, setCsvData] = useState<RestaurantRow[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [uploadResults, setUploadResults] = useState<any>(null)

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    
    if (!file) return

    Papa.parse(file, {
      header: true,
      complete: (results) => {
        const validRows = results.data.filter((row: any) => row.name)
        setCsvData(validRows as RestaurantRow[])
        toast.success(`Loaded ${validRows.length} restaurants from CSV`)
      },
      error: (error) => {
        toast.error('Failed to parse CSV file')
        console.error(error)
      }
    })
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
    },
    maxFiles: 1,
  })

  const handleUpload = async () => {
    if (csvData.length === 0) {
      toast.error('No data to upload')
      return
    }

    setIsUploading(true)
    
    try {
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/bulk-upload`,
        {
          restaurants: csvData.map(row => ({
            name: row.name,
            address: row.address || undefined,
            phone: row.phone || undefined,
            website: row.website || undefined,
            skip_voice_verify: false,
            priority: 'normal'
          })),
          skip_duplicates: true
        }
      )

      setUploadResults(response.data)
      toast.success(`Started analysis for ${response.data.jobs_created} restaurants`)
      setCsvData([])
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to upload restaurants')
    } finally {
      setIsUploading(false)
    }
  }

  const downloadTemplate = () => {
    const template = 'name,address,phone,website\n"Duke\'s La Jolla","1216 Prospect St, La Jolla, CA 92037","(858) 454-5325","https://dukeslajolla.com"\n"The Prado","1549 El Prado, San Diego, CA 92101","(619) 557-9441","https://pradobalboa.com"'
    
    const blob = new Blob([template], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'restaurant_template.csv'
    a.click()
    window.URL.revokeObjectURL(url)
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Upload Area */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card rounded-2xl p-8"
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Upload className="w-6 h-6 text-primary-500" />
            Bulk Upload Restaurants
          </h2>
          <button
            onClick={downloadTemplate}
            className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
          >
            <Download className="w-4 h-4" />
            Download Template
          </button>
        </div>

        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
            isDragActive
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50'
          }`}
        >
          <input {...getInputProps()} />
          
          <Upload className="w-12 h-12 mx-auto text-gray-400 mb-4" />
          
          {isDragActive ? (
            <p className="text-lg font-medium text-primary-600">
              Drop the CSV file here...
            </p>
          ) : (
            <>
              <p className="text-lg font-medium text-gray-700 mb-2">
                Drag & drop a CSV file here
              </p>
              <p className="text-sm text-gray-500">
                or click to select a file
              </p>
            </>
          )}
        </div>

        {/* CSV Preview */}
        {csvData.length > 0 && (
          <div className="mt-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-900">
                Preview ({csvData.length} restaurants)
              </h3>
              <button
                onClick={() => setCsvData([])}
                className="text-sm text-red-600 hover:text-red-700 flex items-center gap-1"
              >
                <X className="w-4 h-4" />
                Clear
              </button>
            </div>
            
            <div className="bg-gray-50 rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium text-gray-700">Name</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-700">Address</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-700">Phone</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-700">Website</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {csvData.slice(0, 5).map((row, index) => (
                      <tr key={index}>
                        <td className="px-4 py-2 text-gray-900">{row.name}</td>
                        <td className="px-4 py-2 text-gray-600">{row.address || '-'}</td>
                        <td className="px-4 py-2 text-gray-600">{row.phone || '-'}</td>
                        <td className="px-4 py-2 text-gray-600 truncate max-w-xs">
                          {row.website || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {csvData.length > 5 && (
                <div className="px-4 py-2 text-sm text-gray-500 bg-gray-100">
                  ... and {csvData.length - 5} more restaurants
                </div>
              )}
            </div>

            {/* Upload Button */}
            <button
              onClick={handleUpload}
              disabled={isUploading}
              className="mt-4 w-full btn-primary flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Upload className="w-5 h-5" />
                  Start Analysis for {csvData.length} Restaurants
                </>
              )}
            </button>
          </div>
        )}
      </motion.div>

      {/* Upload Results */}
      {uploadResults && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card rounded-xl p-6"
        >
          <h3 className="font-semibold text-gray-900 mb-4">Upload Results</h3>
          
          <div className="space-y-3">
            <div className="flex justify-between p-3 bg-green-50 rounded-lg">
              <span className="text-gray-700">Jobs Created:</span>
              <span className="font-bold text-green-700">
                {uploadResults.jobs_created}
              </span>
            </div>
            
            <div className="flex justify-between p-3 bg-blue-50 rounded-lg">
              <span className="text-gray-700">Total Submitted:</span>
              <span className="font-bold text-blue-700">
                {uploadResults.total_submitted}
              </span>
            </div>
          </div>

          {uploadResults.jobs && uploadResults.jobs.length > 0 && (
            <div className="mt-4">
              <p className="text-sm text-gray-600 mb-2">Job IDs:</p>
              <div className="max-h-32 overflow-y-auto bg-gray-50 rounded-lg p-3">
                {uploadResults.jobs.map((job: any, index: number) => (
                  <div key={index} className="text-xs text-gray-600 font-mono">
                    {job.job_id ? job.job_id : `Error: ${job.error}`}
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}
    </div>
  )
}