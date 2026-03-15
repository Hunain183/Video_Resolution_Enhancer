/**
 * API Service for AI Video Enhancer
 */

import axios from 'axios';

// API base URL - uses Vite proxy in development (avoids CORS)
const API_BASE_URL = '/api';

// Create axios instance with large file support
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 600000, // 10 min timeout for large uploads
  maxBodyLength: Infinity,
  maxContentLength: Infinity,
});

// Chunk size for uploads (5MB to stay under proxy limits)
const CHUNK_SIZE = 5 * 1024 * 1024;

/**
 * Video API service
 */
export const videoApi = {
  /**
   * Check API health
   */
  async checkHealth() {
    const response = await api.get('/health');
    return response.data;
  },

  /**
   * Upload video file with chunked upload for large files
   * @param {File} file - Video file to upload
   * @param {Function} onProgress - Progress callback (0-100)
   */
  async uploadVideo(file, onProgress) {
    // For small files (< 5MB), use direct upload
    if (file.size < CHUNK_SIZE) {
      const formData = new FormData();
      formData.append('file', file);

      const response = await api.post('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (event) => {
          if (onProgress && event.total) {
            onProgress((event.loaded / event.total) * 100);
          }
        },
      });
      return response.data;
    }

    // For large files, use chunked upload
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
    const fileId = `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    // Upload each chunk
    for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
      const start = chunkIndex * CHUNK_SIZE;
      const end = Math.min(start + CHUNK_SIZE, file.size);
      const chunk = file.slice(start, end);
      
      const formData = new FormData();
      formData.append('chunk', chunk);
      formData.append('chunk_index', chunkIndex.toString());
      formData.append('total_chunks', totalChunks.toString());
      formData.append('file_id', fileId);
      formData.append('filename', file.name);
      formData.append('file_size', file.size.toString());

      await api.post('/upload-chunk', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      // Update progress
      if (onProgress) {
        const progress = ((chunkIndex + 1) / totalChunks) * 100;
        onProgress(progress);
      }
    }

    // Finalize the upload and get file info
    const finalizeData = new FormData();
    finalizeData.append('file_id', fileId);
    finalizeData.append('filename', file.name);
    
    const response = await api.post('/finalize-upload', finalizeData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    return response.data;
  },

  /**
   * Start video enhancement job
   * @param {Object} options - Enhancement options
   */
  async startEnhancement({
    filePath,
    resolution = 'original',
    upscaleFactor = 2,
    upscalerAlgorithm = 'realesrgan-anime',
    targetFps = 'original',
    denoise = false,
    sharpen = false,
    loopOptimize = false,
    reverseVideo = false,
    losslessOutput = false,
  }) {
    const formData = new FormData();
    formData.append('file_path', filePath);
    formData.append('resolution', resolution);
    formData.append('upscale_factor', upscaleFactor.toString());
    formData.append('upscaler_algorithm', upscalerAlgorithm);
    formData.append('target_fps', targetFps);
    formData.append('denoise', denoise.toString());
    formData.append('sharpen', sharpen.toString());
    formData.append('loop_optimize', loopOptimize.toString());
    formData.append('reverse_video', reverseVideo.toString());
    formData.append('lossless_output', losslessOutput.toString());

    const response = await api.post('/enhance', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },

  /**
   * Get job status
   * @param {string} jobId - Job ID
   */
  async getJobStatus(jobId) {
    const response = await api.get(`/status/${jobId}`);
    return response.data;
  },

  /**
   * Poll job status until completion
   * @param {string} jobId - Job ID
   * @param {Function} onProgress - Progress callback
   * @param {number} interval - Poll interval in ms
   */
  async pollJobStatus(jobId, onProgress, interval = 2000) {
    return new Promise((resolve, reject) => {
      let retryCount = 0;
      const maxRetries = 5;

      const poll = async () => {
        try {
          const status = await this.getJobStatus(jobId);

          if (onProgress) {
            onProgress(status.progress, status.current_step);
          }

          if (status.status === 'completed') {
            resolve(status);
          } else if (status.status === 'failed') {
            reject(new Error(status.message || 'Processing failed'));
          } else {
            retryCount = 0; // Reset on success
            setTimeout(poll, interval);
          }
        } catch (error) {
          retryCount++;
          if (retryCount < maxRetries) {
            console.warn(`Poll retry ${retryCount}/${maxRetries}`);
            setTimeout(poll, interval * 2);
          } else {
            reject(error);
          }
        }
      };

      poll();
    });
  },

  /**
   * Get download URL for completed job
   * @param {string} jobId - Job ID
   */
  getDownloadUrl(jobId) {
    return `${API_BASE_URL}/download/${jobId}`;
  },

  /**
   * Cancel a job
   * @param {string} jobId - Job ID
   */
  async cancelJob(jobId) {
    const response = await api.delete(`/job/${jobId}`);
    return response.data;
  },
};

export default videoApi;
