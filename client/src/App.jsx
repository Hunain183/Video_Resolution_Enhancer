import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { useDropzone } from 'react-dropzone';
import { videoApi } from './api';

// Icons as inline SVGs
const Icons = {
  Upload: () => (
    <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
    </svg>
  ),
  Video: () => (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
    </svg>
  ),
  Download: () => (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
    </svg>
  ),
  Sparkles: () => (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
    </svg>
  ),
  Refresh: () => (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),
  Check: () => (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  ),
  X: () => (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
};

// Toggle Switch Component
function ToggleSwitch({ enabled, onChange, label }) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-dark-200 text-sm">{label}</span>
      <button
        type="button"
        onClick={() => onChange(!enabled)}
        className={`toggle-switch ${enabled ? 'active' : ''}`}
      />
    </div>
  );
}

// Select Component
function Select({ label, value, onChange, options }) {
  return (
    <div className="space-y-2">
      <label className="block text-dark-300 text-sm font-medium">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-dark-800 border border-dark-600 rounded-lg px-4 py-3 text-dark-100 
                   focus:outline-none focus:ring-2 focus:ring-neon-cyan focus:border-transparent
                   transition-all duration-300"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

// Progress Bar Component
function ProgressBar({ progress, status, currentStep }) {
  return (
    <div className="space-y-3">
      <div className="flex justify-between items-center text-sm">
        <span className="text-neon-cyan font-medium">{currentStep || status}</span>
        <span className="text-dark-300 font-mono">{progress.toFixed(2)}%</span>
      </div>
      <div className="h-3 bg-dark-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-neon-green to-neon-cyan rounded-full transition-all duration-300 progress-animate"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}

// Video Info Display
function VideoInfo({ info }) {
  if (!info) return null;

  return (
    <div className="grid grid-cols-2 gap-4 p-4 bg-dark-800/50 rounded-lg text-sm">
      <div>
        <span className="text-dark-400">Resolution</span>
        <p className="text-dark-100 font-mono">{info.width} × {info.height}</p>
      </div>
      <div>
        <span className="text-dark-400">Frame Rate</span>
        <p className="text-dark-100 font-mono">{info.fps} FPS</p>
      </div>
      <div>
        <span className="text-dark-400">Duration</span>
        <p className="text-dark-100 font-mono">{info.duration?.toFixed(2)}s</p>
      </div>
      <div>
        <span className="text-dark-400">Codec</span>
        <p className="text-dark-100 font-mono">{info.codec}</p>
      </div>
    </div>
  );
}

// Main App Component
export default function App() {
  const ESTIMATOR_CALIBRATION_KEY = 'videoEnhancerEstimatorCalibrationV1';

  const RESOLUTION_MAP = {
    '1080p': [1920, 1080],
    '1440p': [2560, 1440],
    '4k': [3840, 2160],
  };

  const TARGET_FPS_MAP = {
    '60': 60,
    '120': 120,
  };

  // State
  const [file, setFile] = useState(null);
  const [uploadData, setUploadData] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);

  // Enhancement options
  const [resolution, setResolution] = useState('original');
  const [upscaleFactor, setUpscaleFactor] = useState('2');
  const [upscalerAlgorithm, setUpscalerAlgorithm] = useState('realesrgan');
  const [targetFps, setTargetFps] = useState('original');
  const [denoise, setDenoise] = useState(false);
  const [sharpen, setSharpen] = useState(false);
  const [loopOptimize, setLoopOptimize] = useState(false);
  const [reverseVideo, setReverseVideo] = useState(false);
  const [losslessOutput, setLosslessOutput] = useState(false);

  // Processing state
  const [status, setStatus] = useState('idle'); // idle, uploading, processing, completed, error
  const [jobId, setJobId] = useState(null);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [result, setResult] = useState(null);
  const [cpuCalibration, setCpuCalibration] = useState({ factor: 1, samples: 0 });
  const [runtimeHealth, setRuntimeHealth] = useState(null);

  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

  const estimateProfile = useCallback((input, options) => {
    const inputWidth = Number(input.width) || 0;
    const inputHeight = Number(input.height) || 0;
    const inputFps = Number(input.fps) || 30;
    const durationSec = Number(input.duration) || 0;
    const inputSizeMb = Number(input.sizeMb) || 0;

    if (!inputWidth || !inputHeight || !durationSec || !inputSizeMb) {
      return null;
    }

    let outputWidth = inputWidth;
    let outputHeight = inputHeight;

    const upscaleMultiplier = Math.max(1, Number(options.upscaleFactor) || 1);
    const aiUpscaleEnabled = options.upscalerAlgorithm === 'realesrgan' && upscaleMultiplier > 1;

    if (aiUpscaleEnabled) {
      outputWidth = Math.round(outputWidth * upscaleMultiplier);
      outputHeight = Math.round(outputHeight * upscaleMultiplier);
    }

    const targetResolution = RESOLUTION_MAP[options.resolution];
    if (targetResolution) {
      [outputWidth, outputHeight] = targetResolution;
    }

    const selectedFps = TARGET_FPS_MAP[options.targetFps];
    const outputFps = selectedFps && selectedFps > inputFps ? selectedFps : inputFps;

    const pixelRatio = (outputWidth * outputHeight) / (inputWidth * inputHeight);
    const fpsRatio = outputFps / inputFps;
    const interpolationEnabled = outputFps > inputFps;
    const filterCount = Number(options.denoise) + Number(options.sharpen) + Number(options.loopOptimize) + Number(options.reverseVideo);

    let sizeLowMb;
    let sizeHighMb;

    if (options.losslessOutput) {
      sizeLowMb = inputSizeMb * Math.max(3.0, pixelRatio * fpsRatio * 3.0);
      sizeHighMb = inputSizeMb * Math.max(8.0, pixelRatio * fpsRatio * 10.0);
    } else {
      sizeLowMb = inputSizeMb * Math.max(0.7, pixelRatio * fpsRatio * 0.8);
      sizeHighMb = inputSizeMb * Math.max(1.6, pixelRatio * fpsRatio * 2.2);
    }

    const cpuRealtimeFactor = (
      (aiUpscaleEnabled ? 25 * upscaleMultiplier : 1.4) *
      (interpolationEnabled ? 2.4 * fpsRatio : 1.0) *
      (options.losslessOutput ? 0.95 : 1.05) *
      (1 + filterCount * 0.15)
    );

    const gpuRealtimeFactor = (
      (aiUpscaleEnabled ? 2.8 * upscaleMultiplier : 0.8) *
      (interpolationEnabled ? 1.7 * fpsRatio : 1.0) *
      (options.losslessOutput ? 0.9 : 1.0) *
      (1 + filterCount * 0.12)
    );

    return {
      outputWidth,
      outputHeight,
      outputFps,
      sizeLowMb,
      sizeHighMb,
      baseCpuMinutes: (durationSec * cpuRealtimeFactor) / 60,
      baseGpuMinutes: (durationSec * gpuRealtimeFactor) / 60,
    };
  }, [RESOLUTION_MAP, TARGET_FPS_MAP]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(ESTIMATOR_CALIBRATION_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      const factor = Number(parsed?.factor);
      const samples = Number(parsed?.samples);
      if (!Number.isFinite(factor) || factor <= 0) return;
      setCpuCalibration({
        factor: clamp(factor, 0.25, 4),
        samples: Number.isFinite(samples) && samples > 0 ? Math.floor(samples) : 0,
      });
    } catch {
      // Ignore corrupt calibration cache.
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    const loadHealth = async () => {
      try {
        const data = await videoApi.checkHealth();
        if (!cancelled) {
          setRuntimeHealth(data);
        }
      } catch {
        if (!cancelled) {
          setRuntimeHealth(null);
        }
      }
    };

    loadHealth();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const processingSec = Number(result?.processing_time);
    const input = result?.input;
    const settings = result?.settings;

    if (!result || !input || !settings || !Number.isFinite(processingSec) || processingSec <= 0) {
      return;
    }

    const profile = estimateProfile(
      {
        width: input.width,
        height: input.height,
        fps: input.fps,
        duration: input.duration,
        sizeMb: Number(file?.size || uploadData?.file_size || 0) / (1024 * 1024),
      },
      {
        resolution: settings.resolution,
        upscaleFactor: settings.upscale_factor,
        upscalerAlgorithm: settings.upscaler_algorithm,
        targetFps: settings.target_fps,
        denoise: settings.denoise,
        sharpen: settings.sharpen,
        loopOptimize: settings.loop_optimize,
        reverseVideo: settings.reverse_video,
        losslessOutput: settings.lossless_output,
      }
    );

    if (!profile || profile.baseCpuMinutes <= 0) return;

    const actualMinutes = processingSec / 60;
    const rawFactor = actualMinutes / profile.baseCpuMinutes;
    const measuredFactor = clamp(rawFactor, 0.2, 5);

    setCpuCalibration((prev) => {
      const nextSamples = prev.samples + 1;
      const alpha = 0.35;
      const blended = prev.samples > 0
        ? (prev.factor * (1 - alpha)) + (measuredFactor * alpha)
        : measuredFactor;

      const next = {
        factor: clamp(blended, 0.25, 4),
        samples: nextSamples,
      };

      try {
        window.localStorage.setItem(ESTIMATOR_CALIBRATION_KEY, JSON.stringify(next));
      } catch {
        // Ignore storage failures.
      }

      return next;
    });
  }, [result, file, uploadData, estimateProfile]);

  // Helper to extract error message from various error formats
  const getErrorMessage = (err, fallback = 'An error occurred') => {
    if (err.response?.data?.detail) {
      const detail = err.response.data.detail;
      if (typeof detail === 'string') return detail;
      if (Array.isArray(detail)) {
        return detail.map(e => e.msg || e.message || String(e)).join(', ');
      }
      if (typeof detail === 'object') {
        return detail.msg || detail.message || JSON.stringify(detail);
      }
    }
    return err.message || fallback;
  };

  // Poll for job status
  useEffect(() => {
    if (!jobId || status !== 'processing') return;

    const pollStatus = async () => {
      try {
        const jobStatus = await videoApi.getJobStatus(jobId);
        const normalizedStatus = String(jobStatus.status || '').toLowerCase();

        setProgress(jobStatus.progress || 0);
        setCurrentStep(jobStatus.current_step || '');

        if (
          normalizedStatus === 'completed' ||
          (jobStatus.progress >= 100 && String(jobStatus.current_step || '').toLowerCase().includes('complete'))
        ) {
          setStatus('completed');
          setResult(jobStatus.result || null);
        } else if (normalizedStatus === 'failed') {
          setStatus('error');
          setErrorMessage(jobStatus.message || 'Processing failed');
        }
      } catch (err) {
        console.error('Status poll error:', err);
        // Don't fail on poll errors, just retry
      }
    };

    pollStatus();
    const interval = setInterval(pollStatus, 1500);
    return () => clearInterval(interval);
  }, [jobId, status]);

  // Handle file drop
  const onDrop = useCallback(async (acceptedFiles) => {
    const videoFile = acceptedFiles[0];
    if (!videoFile) return;

    setFile(videoFile);
    setPreviewUrl(URL.createObjectURL(videoFile));
    setStatus('uploading');
    setProgress(0);
    setErrorMessage('');
    setResult(null);

    try {
      const data = await videoApi.uploadVideo(videoFile, (p) => setProgress(p));
      setUploadData(data);
      setStatus('idle');
      setProgress(0);
    } catch (err) {
      setStatus('error');
      setErrorMessage(getErrorMessage(err, 'Upload failed'));
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.mov', '.webm', '.gif', '.avi', '.mkv']
    },
    maxFiles: 1,
    disabled: status === 'processing' || status === 'uploading'
  });

  // Start enhancement
  const handleEnhance = async () => {
    if (!uploadData?.file_path) return;

    setStatus('processing');
    setProgress(0);
    setCurrentStep('Starting');
    setErrorMessage('');

    try {
      const job = await videoApi.startEnhancement({
        filePath: uploadData.file_path,
        resolution,
        upscaleFactor: parseInt(upscaleFactor),
        upscalerAlgorithm,
        targetFps,
        denoise,
        sharpen,
        loopOptimize,
        reverseVideo,
        losslessOutput,
      });

      setJobId(job.job_id);
    } catch (err) {
      setStatus('error');
      setErrorMessage(getErrorMessage(err, 'Failed to start processing'));
    }
  };

  // Download result
  const handleDownload = () => {
    if (!jobId) return;
    const downloadUrl = videoApi.getDownloadUrl(jobId);
    const popup = window.open(downloadUrl, '_blank');
    if (!popup) {
      window.location.href = downloadUrl;
    }
  };

  // Reset
  const handleReset = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(null);
    setUploadData(null);
    setPreviewUrl(null);
    setJobId(null);
    setStatus('idle');
    setProgress(0);
    setCurrentStep('');
    setErrorMessage('');
    setResult(null);
  };

  const isProcessing = status === 'processing' || status === 'uploading';
  const canEnhance = uploadData && status === 'idle';

  const estimatedOutput = useMemo(() => {
    const info = uploadData?.video_info;
    if (!info) return null;

    const profile = estimateProfile(
      {
        width: info.width,
        height: info.height,
        fps: info.fps,
        duration: info.duration,
        sizeMb: Number((uploadData?.file_size || file?.size || 0) / (1024 * 1024)),
      },
      {
        resolution,
        upscaleFactor,
        upscalerAlgorithm,
        targetFps,
        denoise,
        sharpen,
        loopOptimize,
        reverseVideo,
        losslessOutput,
      }
    );

    if (!profile) return null;

    const calibratedCpuMinutes = profile.baseCpuMinutes * cpuCalibration.factor;
    const gpuAvailable = Boolean(runtimeHealth?.gpu?.available);
    const configuredTile = Number(runtimeHealth?.processing?.esrgan_tile);

    // Very small tile values (like 8) massively increase ESRGAN runtime on CPU.
    let tilePenalty = 1;
    if (upscalerAlgorithm === 'realesrgan') {
      if (Number.isFinite(configuredTile) && configuredTile > 0) {
        tilePenalty = Math.max(1, 200 / configuredTile);
      }

      if (!gpuAvailable) {
        tilePenalty *= 1.6;
      }
    }

    const adjustedCpuMinutes = calibratedCpuMinutes * tilePenalty;

    return {
      outputWidth: profile.outputWidth,
      outputHeight: profile.outputHeight,
      outputFps: profile.outputFps,
      sizeLowMb: profile.sizeLowMb,
      sizeHighMb: profile.sizeHighMb,
      cpuLowMin: adjustedCpuMinutes * 0.7,
      cpuHighMin: adjustedCpuMinutes * 1.35,
      gpuLowMin: profile.baseGpuMinutes * 0.7,
      gpuHighMin: profile.baseGpuMinutes * 1.35,
      gpuAvailable,
      configuredTile: Number.isFinite(configuredTile) ? configuredTile : null,
      tilePenalty,
    };
  }, [
    uploadData,
    file,
    resolution,
    upscaleFactor,
    upscalerAlgorithm,
    targetFps,
    denoise,
    sharpen,
    loopOptimize,
    reverseVideo,
    losslessOutput,
    cpuCalibration.factor,
    estimateProfile,
    runtimeHealth,
  ]);

  const formatSize = (mb) => {
    if (mb >= 1024) return `${(mb / 1024).toFixed(2)} GB`;
    return `${mb.toFixed(0)} MB`;
  };

  const formatDuration = (minutes) => {
    if (minutes >= 60) return `${(minutes / 60).toFixed(1)} h`;
    if (minutes < 1) return '<1 min';
    return `${Math.round(minutes)} min`;
  };

  return (
    <div className="min-h-screen grid-pattern">
      {/* Header */}
      <header className="border-b border-dark-700/50 bg-dark-900/80 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-neon-cyan to-neon-green flex items-center justify-center">
              <Icons.Sparkles />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">AI Video Enhancer</h1>
              <p className="text-dark-400 text-sm">Upscale • Interpolate • Optimize</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left Column - Upload & Preview */}
          <div className="space-y-6">
            {/* Upload Zone */}
            <div
              {...getRootProps()}
              className={`
                relative border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer
                transition-all duration-300 
                ${isDragActive ? 'dropzone-active' : 'border-dark-600 hover:border-dark-500'}
                ${isProcessing ? 'opacity-50 cursor-not-allowed' : ''}
              `}
            >
              <input {...getInputProps()} />

              {previewUrl ? (
                <div className="space-y-4">
                  <video
                    src={previewUrl}
                    className="w-full max-h-64 object-contain rounded-lg"
                    controls
                    muted
                    loop
                  />
                  <p className="text-dark-300 text-sm">
                    {file?.name} • {(file?.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                </div>
              ) : (
                <div className="space-y-4 py-8">
                  <div className="text-neon-cyan mx-auto">
                    <Icons.Upload />
                  </div>
                  <div>
                    <p className="text-dark-100 font-medium">
                      {isDragActive ? 'Drop video here' : 'Drag & drop video'}
                    </p>
                    <p className="text-dark-400 text-sm mt-1">
                      or click to browse • MP4, MOV, WebM, GIF
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Video Info */}
            {uploadData?.video_info && (
              <div className="neon-border rounded-xl p-4 bg-dark-900/50">
                <h3 className="text-dark-200 font-medium mb-3 flex items-center gap-2">
                  <Icons.Video />
                  Video Information
                </h3>
                <VideoInfo info={uploadData.video_info} />
              </div>
            )}

            {/* Result Info */}
            {result && (
              <div className="neon-border rounded-xl p-4 bg-dark-900/50 border-neon-green/30">
                <h3 className="text-neon-green font-medium mb-3 flex items-center gap-2">
                  <Icons.Check />
                  Enhancement Complete
                </h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-dark-400">Output Resolution</span>
                    <p className="text-dark-100 font-mono">
                      {result.output?.width} × {result.output?.height}
                    </p>
                  </div>
                  <div>
                    <span className="text-dark-400">Output FPS</span>
                    <p className="text-dark-100 font-mono">{result.output?.fps} FPS</p>
                  </div>
                  <div>
                    <span className="text-dark-400">Upscaler</span>
                    <p className="text-dark-100 font-mono">
                      {result.settings?.upscaler_algorithm || 'realesrgan'}
                    </p>
                  </div>
                  <div>
                    <span className="text-dark-400">File Size</span>
                    <p className="text-dark-100 font-mono">
                      {(result.output?.file_size / (1024 * 1024)).toFixed(2)} MB
                    </p>
                  </div>
                  <div>
                    <span className="text-dark-400">Processing Time</span>
                    <p className="text-dark-100 font-mono">{result.processing_time}s</p>
                  </div>
                  <div>
                    <span className="text-dark-400">Reversed</span>
                    <p className="text-dark-100 font-mono">{result.settings?.reverse_video ? 'Yes' : 'No'}</p>
                  </div>
                  <div>
                    <span className="text-dark-400">Lossless</span>
                    <p className="text-dark-100 font-mono">{result.settings?.lossless_output ? 'Yes' : 'No'}</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Column - Options & Actions */}
          <div className="space-y-6">
            {/* Enhancement Options */}
            <div className="neon-border rounded-2xl p-6 bg-dark-900/50">
              <h2 className="text-lg font-semibold text-white mb-6">Enhancement Options</h2>

              <div className="space-y-5">
                {/* Resolution */}
                <Select
                  label="Target Resolution"
                  value={resolution}
                  onChange={setResolution}
                  options={[
                    { value: 'original', label: 'Original' },
                    { value: '1080p', label: '1080p (1920×1080)' },
                    { value: '1440p', label: '1440p (2560×1440)' },
                    { value: '4k', label: '4K (3840×2160)' },
                  ]}
                />

                {/* Upscale Factor */}
                <Select
                  label="AI Upscale Factor"
                  value={upscaleFactor}
                  onChange={setUpscaleFactor}
                  options={[
                    { value: '1', label: 'Original (No Upscale)' },
                    { value: '2', label: '2× Upscale' },
                    { value: '4', label: '4× Upscale' },
                  ]}
                />

                {/* Upscaling Algorithm */}
                <Select
                  label="Upscaling Algorithm"
                  value={upscalerAlgorithm}
                  onChange={setUpscalerAlgorithm}
                  options={[
                    { value: 'original', label: 'None' },
                    { value: 'realesrgan', label: 'Real-ESRGAN' },
                    { value: 'lanczos', label: 'Lanczos' },
                  ]}
                />

                {/* Target FPS */}
                <Select
                  label="Target Frame Rate"
                  value={targetFps}
                  onChange={setTargetFps}
                  options={[
                    { value: 'original', label: 'Original FPS' },
                    { value: '60', label: '60 FPS' },
                    { value: '120', label: '120 FPS' },
                  ]}
                />

                {/* Toggles */}
                <div className="border-t border-dark-700 pt-4 space-y-1">
                  <ToggleSwitch
                    label="Denoise"
                    enabled={denoise}
                    onChange={setDenoise}
                  />
                  <ToggleSwitch
                    label="Sharpen"
                    enabled={sharpen}
                    onChange={setSharpen}
                  />
                  <ToggleSwitch
                    label="Loop Optimization"
                    enabled={loopOptimize}
                    onChange={setLoopOptimize}
                  />
                  <ToggleSwitch
                    label="Reverse Video"
                    enabled={reverseVideo}
                    onChange={setReverseVideo}
                  />
                  <ToggleSwitch
                    label="Lossless Output"
                    enabled={losslessOutput}
                    onChange={setLosslessOutput}
                  />
                </div>

                {uploadData?.video_info && estimatedOutput && (
                  <div className="border-t border-dark-700 pt-4 rounded-lg bg-dark-800/40 p-4 space-y-3">
                    <h3 className="text-dark-100 font-medium">Estimated Output</h3>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="text-dark-400">Resolution</span>
                        <p className="text-dark-100 font-mono">
                          {estimatedOutput.outputWidth} × {estimatedOutput.outputHeight}
                        </p>
                      </div>
                      <div>
                        <span className="text-dark-400">Frame Rate</span>
                        <p className="text-dark-100 font-mono">{estimatedOutput.outputFps.toFixed(0)} FPS</p>
                      </div>
                      <div>
                        <span className="text-dark-400">Estimated Size</span>
                        <p className="text-dark-100 font-mono">
                          {formatSize(estimatedOutput.sizeLowMb)} - {formatSize(estimatedOutput.sizeHighMb)}
                        </p>
                      </div>
                      <div>
                        <span className="text-dark-400">Estimated Time (CPU)</span>
                        <p className="text-dark-100 font-mono">
                          {formatDuration(estimatedOutput.cpuLowMin)} - {formatDuration(estimatedOutput.cpuHighMin)}
                        </p>
                      </div>
                      <div className="col-span-2">
                        <span className="text-dark-400">Estimated Time (GPU)</span>
                        <p className="text-dark-100 font-mono">
                          {estimatedOutput.gpuAvailable
                            ? `${formatDuration(estimatedOutput.gpuLowMin)} - ${formatDuration(estimatedOutput.gpuHighMin)}`
                            : 'GPU not available'}
                        </p>
                      </div>
                    </div>
                    {estimatedOutput.configuredTile !== null && estimatedOutput.configuredTile <= 16 && upscalerAlgorithm === 'realesrgan' && (
                      <p className="text-amber-300 text-xs">
                        Warning: ESRGAN tile={estimatedOutput.configuredTile} is very small and can drastically increase processing time.
                      </p>
                    )}
                    <p className="text-dark-500 text-xs">
                      Estimates vary by content complexity, hardware, and selected options.
                    </p>
                    <p className="text-dark-500 text-xs">
                      CPU estimate calibration: ×{cpuCalibration.factor.toFixed(2)} ({cpuCalibration.samples} sample{cpuCalibration.samples === 1 ? '' : 's'}).
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Progress */}
            {isProcessing && (
              <div className="neon-border rounded-xl p-6 bg-dark-900/50">
                <ProgressBar
                  progress={progress}
                  status={status}
                  currentStep={currentStep}
                />
              </div>
            )}

            {/* Error Message */}
            {errorMessage && (
              <div className="rounded-xl p-4 bg-red-500/10 border border-red-500/30">
                <div className="flex items-center gap-2 text-red-400">
                  <Icons.X />
                  <span className="font-medium">Error</span>
                </div>
                <p className="text-red-300 text-sm mt-2">{errorMessage}</p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-3">
              {status === 'completed' ? (
                <>
                  <button
                    onClick={handleDownload}
                    className="flex-1 btn-neon bg-gradient-to-r from-neon-green to-neon-cyan text-dark-900 
                               font-semibold py-4 px-6 rounded-xl flex items-center justify-center gap-2
                               hover:shadow-neon-green transition-all duration-300"
                  >
                    <Icons.Download />
                    Download Enhanced Video
                  </button>
                  <button
                    onClick={handleReset}
                    className="px-6 py-4 rounded-xl bg-dark-700 text-dark-200 hover:bg-dark-600 
                               transition-all duration-300"
                  >
                    <Icons.Refresh />
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={handleEnhance}
                    disabled={!canEnhance || isProcessing}
                    className={`
                      flex-1 btn-neon font-semibold py-4 px-6 rounded-xl 
                      flex items-center justify-center gap-2 transition-all duration-300
                      ${canEnhance && !isProcessing
                        ? 'bg-gradient-to-r from-neon-cyan to-neon-blue text-dark-900 hover:shadow-neon-cyan'
                        : 'bg-dark-700 text-dark-400 cursor-not-allowed'
                      }
                    `}
                  >
                    {isProcessing ? (
                      <>
                        <svg className="w-5 h-5 spinner" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        {status === 'uploading' ? 'Uploading...' : 'Processing...'}
                      </>
                    ) : (
                      <>
                        <Icons.Sparkles />
                        Enhance Video
                      </>
                    )}
                  </button>
                  {uploadData && (
                    <button
                      onClick={handleReset}
                      disabled={isProcessing}
                      className="px-6 py-4 rounded-xl bg-dark-700 text-dark-200 hover:bg-dark-600 
                                 transition-all duration-300 disabled:opacity-50"
                    >
                      <Icons.Refresh />
                    </button>
                  )}
                </>
              )}
            </div>

            {/* Features List */}
            <div className="text-dark-400 text-sm space-y-2">
              <p>• Real-ESRGAN AI upscaling for maximum quality</p>
              <p>• RIFE frame interpolation for smooth motion</p>
              <p>• H.265/HEVC encoding (15-50 Mbps)</p>
              <p>• GPU acceleration when available</p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-dark-700/50 mt-12">
        <div className="max-w-6xl mx-auto px-6 py-6 text-center text-dark-500 text-sm">
          AI Video Enhancer • Real-ESRGAN + RIFE Pipeline
        </div>
      </footer>
    </div>
  );
}
