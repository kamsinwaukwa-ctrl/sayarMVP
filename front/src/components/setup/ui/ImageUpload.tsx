/**
 * Image upload component for logo and product images
 */

import { useState, useRef } from 'react'
import { Upload, X, Image as ImageIcon, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { cn } from '@/lib/utils'

interface ImageUploadProps {
  value?: string
  onChange: (url: string) => void
  onRemove: () => void
  placeholder?: string
  accept?: string
  maxSize?: number // in bytes
  className?: string
}

export function ImageUpload({
  value,
  onChange,
  onRemove,
  placeholder = "Click to upload an image",
  accept = "image/*",
  maxSize = 5 * 1024 * 1024, // 5MB default
  className,
}: ImageUploadProps) {
  const [isUploading, setIsUploading] = useState(false)
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = async (file: File) => {
    if (file.size > maxSize) {
      alert(`File size must be less than ${Math.round(maxSize / 1024 / 1024)}MB`)
      return
    }

    if (!file.type.startsWith('image/')) {
      alert('Please select an image file')
      return
    }

    setIsUploading(true)
    try {
      // Use the new media API wrapper
      const { mediaApi } = await import('@/lib/api/media')
      const result = await mediaApi.uploadLogo(file)

      // Use the secure Cloudinary URL from the response
      onChange(result.logo.url)
    } catch (error) {
      console.error('Upload error:', error)
      console.error('Error details:', {
        message: error instanceof Error ? error.message : 'Unknown error',
        status: (error as any)?.status,
        statusText: (error as any)?.statusText
      })

      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      alert(`Failed to upload image: ${errorMessage}. Please try again.`)
    } finally {
      setIsUploading(false)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)

    const file = e.dataTransfer.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
  }

  const formatFileSize = (bytes: number) => {
    return `${Math.round(bytes / 1024 / 1024)}MB`
  }

  if (value) {
    return (
      <div className={cn("relative group", className)}>
        <div className="relative border-2 border-gray-300 rounded-lg overflow-hidden">
          <img
            src={value}
            alt="Uploaded image"
            className="w-full h-32 object-cover"
          />
          <div className="absolute inset-0 bg-black bg-opacity-50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            <Button
              type="button"
              variant="destructive"
              size="sm"
              onClick={onRemove}
            >
              <X className="w-4 h-4 mr-1" />
              Remove
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={cn("w-full", className)}>
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={handleFileChange}
        className="hidden"
      />

      <div
        onClick={() => fileInputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={cn(
          "border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors",
          dragActive
            ? "border-blue-500 bg-blue-50"
            : "border-gray-300 hover:border-gray-400",
          isUploading && "pointer-events-none opacity-50"
        )}
      >
        {isUploading ? (
          <div className="flex flex-col items-center">
            <Loader2 className="h-8 w-8 text-blue-500 animate-spin mb-2" />
            <p className="text-sm text-gray-600">Uploading...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center">
            <div className="flex items-center justify-center w-12 h-12 bg-gray-100 rounded-full mb-3">
              {dragActive ? (
                <Upload className="h-6 w-6 text-blue-500" />
              ) : (
                <ImageIcon className="h-6 w-6 text-gray-400" />
              )}
            </div>
            <p className="text-sm font-medium text-gray-900 mb-1">
              {placeholder}
            </p>
            <p className="text-xs text-gray-500">
              Drag and drop or click to browse
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Max size: {formatFileSize(maxSize)}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}