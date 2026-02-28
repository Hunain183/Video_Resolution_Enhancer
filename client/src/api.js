/**
 * API Service for AI Video Enhancer
 */

import axios from 'axios';

// API base URL - uses Vite proxy in development
const API_BASE_URL = '/api';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 min timeout for large uploads
});

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
   * Upload video file with progress tracking
   * @param {File} file - Video file to upload
   * @param {Function} onProgress - Progress callback (0-100)
   */
  async uploadVideo(file, onProgress) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (event) => {
        if (onProgress && event.total) {
          const progress = (event.loaded / event.total) * 100;
          onProgress(progress);
        }
      },
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
    targetFps = 'original',
    denoise = false,
    sharpen = false,
    loopOptimize = false,
  }) {
    const formData = new FormData();
    formData.append('file_path', filePath);
    formData.append('resolution', resolution);
    formData.append('upscale_factor', upscaleFactor.toString());
    formData.append('target_fps', targetFps);
    formData.append('denoise', denoise.toString());
    formData.append('sharpen', sharpen.toString());
    formData.append('loop_optimize', loopOptimize.toString());

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
