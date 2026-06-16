import { useCallback, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { uploadDocument } from '../api/documents'

const ACCEPTED = '.pdf,.docx,.doc,.pptx,.ppt,.xlsx,.xls,.csv,.png,.jpg,.jpeg,.tiff,.tif'

interface Props {
  sessionId: string
}

export default function UploadZone({ sessionId }: Props) {
  const qc = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragActive, setDragActive] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [count, setCount] = useState(0)

  const handleFiles = useCallback(
    async (files: FileList) => {
      const arr = Array.from(files)
      setCount(arr.length)
      setUploading(true)
      try {
        await Promise.all(arr.map((f) => uploadDocument(sessionId, f)))
        qc.invalidateQueries({ queryKey: ['documents', sessionId] })
      } finally {
        setUploading(false)
        setCount(0)
      }
    },
    [sessionId, qc],
  )

  function onDragOver(e: React.DragEvent) {
    e.preventDefault()
    setDragActive(true)
  }

  function onDragLeave(e: React.DragEvent) {
    e.preventDefault()
    setDragActive(false)
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragActive(false)
    if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files)
  }

  function onChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files?.length) {
      handleFiles(e.target.files)
      e.target.value = ''
    }
  }

  return (
    <div
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={() => !uploading && inputRef.current?.click()}
      className={`rounded-xl border-2 border-dashed p-10 text-center transition cursor-pointer select-none ${
        uploading
          ? 'border-blue-300 bg-blue-50/60 cursor-not-allowed'
          : dragActive
            ? 'border-blue-500 bg-blue-50 scale-[1.005]'
            : 'border-gray-200 bg-white hover:border-blue-300 hover:bg-blue-50/30'
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPTED}
        className="hidden"
        onChange={onChange}
        disabled={uploading}
      />

      {uploading ? (
        <>
          <div className="w-9 h-9 border-[3px] border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm font-medium text-blue-700">
            Uploading {count} file{count !== 1 ? 's' : ''}…
          </p>
          <p className="text-xs text-blue-400 mt-1">Please wait</p>
        </>
      ) : (
        <>
          <div className="w-12 h-12 rounded-xl bg-gray-100 flex items-center justify-center mx-auto mb-3 text-xl">
            {dragActive ? '📥' : '☁️'}
          </div>
          <p className="text-sm font-medium text-gray-700 mb-1">
            {dragActive ? 'Drop files here' : 'Drag & drop or click to upload'}
          </p>
          <p className="text-xs text-gray-400">
            PDF · Word · Excel · PowerPoint · CSV · Images
          </p>
        </>
      )}
    </div>
  )
}
