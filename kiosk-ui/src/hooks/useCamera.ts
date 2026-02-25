import { useEffect, useRef, useCallback, useState } from "react";
import { detectFaces } from "../services/api";

interface UseCameraOptions {
  enabled?: boolean;
  fps?: number;
  onFaceDetected?: (faces: import("../types").DetectedFace[]) => void;
}

export function useCamera({ enabled = false, fps = 2, onFaceDetected }: UseCameraOptions = {}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: 640, height: 480 },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setHasPermission(true);
    } catch {
      setHasPermission(false);
    }
  }, []);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const captureFrame = useCallback((): string | null => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < 2) return null;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;

    ctx.drawImage(video, 0, 0);
    return canvas.toDataURL("image/jpeg", 0.7);
  }, []);

  useEffect(() => {
    if (!enabled) {
      stopCamera();
      return;
    }

    startCamera();

    return () => stopCamera();
  }, [enabled, startCamera, stopCamera]);

  useEffect(() => {
    if (!enabled || !hasPermission || !onFaceDetected) return;

    intervalRef.current = setInterval(async () => {
      const frame = captureFrame();
      if (!frame) return;

      try {
        const result = await detectFaces(frame);
        if (result.faces.length > 0) {
          onFaceDetected(result.faces);
        }
      } catch {
        // Detection failed silently — will retry next frame
      }
    }, 1000 / fps);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [enabled, hasPermission, fps, onFaceDetected, captureFrame]);

  return { videoRef, canvasRef, hasPermission, captureFrame };
}
