import { useEffect, useRef, useState } from 'react';
import jsQR from 'jsqr';

/**
 * Camera QR scanner (laptop webcam or phone camera).
 * Calls onScan(text) when a QR code is read. The same code is ignored for 4 seconds
 * so one scan does not fire several requests.
 */
export default function QrScanner({ onScan }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const onScanRef = useRef(onScan);
  onScanRef.current = onScan;
  const [error, setError] = useState('');
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let stream = null;
    let timer = null;
    let stopped = false;
    let last = { text: '', at: 0 };

    function tick() {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (stopped || !video || !canvas) return;
      if (video.readyState === video.HAVE_ENOUGH_DATA && video.videoWidth) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const image = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const code = jsQR(image.data, image.width, image.height, { inversionAttempts: 'dontInvert' });
        if (code && code.data) {
          const now = Date.now();
          if (code.data !== last.text || now - last.at > 4000) {
            last = { text: code.data, at: now };
            onScanRef.current(code.data);
          }
        }
      }
      timer = setTimeout(tick, 200);
    }

    async function start() {
      if (!navigator.mediaDevices?.getUserMedia) {
        setError('Camera is not available here. Open the app on http://localhost:5173 (or use HTTPS) and use a modern browser.');
        return;
      }
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: 'environment' } },
          audio: false,
        });
        if (stopped) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        const video = videoRef.current;
        video.srcObject = stream;
        video.setAttribute('playsinline', 'true');
        await video.play();
        setReady(true);
        tick();
      } catch (e) {
        setError(
          e?.name === 'NotAllowedError'
            ? 'Camera permission was blocked. Allow the camera for this site and try again.'
            : e?.name === 'NotFoundError'
              ? 'No camera was found on this device.'
              : 'Unable to start the camera.'
        );
      }
    }

    start();
    return () => {
      stopped = true;
      clearTimeout(timer);
      if (stream) stream.getTracks().forEach((t) => t.stop());
    };
  }, []);

  return (
    <div>
      {error ? (
        <div className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</div>
      ) : (
        <div className="relative overflow-hidden rounded-2xl bg-black">
          <video ref={videoRef} muted playsInline className="aspect-video w-full object-cover" />
          {ready && (
            <div className="pointer-events-none absolute inset-0 grid place-items-center">
              <div className="h-48 w-48 rounded-2xl border-4 border-green-400/80" />
            </div>
          )}
          {!ready && <p className="absolute inset-0 grid place-items-center text-sm text-white">Starting camera…</p>}
        </div>
      )}
      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}