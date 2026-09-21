import { useEffect, useRef, useState } from "react";

function microphoneError(error) {
  const messages = {
    NotFoundError:
      "No microphone was detected. Connect or enable an input device, then check your browser’s microphone settings.",
    DevicesNotFoundError:
      "No microphone was detected. Connect or enable an input device, then check your browser’s microphone settings.",
    NotAllowedError:
      "Microphone access is blocked. Allow microphone access for this site in your browser settings and try again.",
    PermissionDeniedError:
      "Microphone access is blocked. Allow microphone access for this site in your browser settings and try again.",
    NotReadableError:
      "Your microphone is being used by another application or could not be opened.",
    AbortError: "The browser could not start the microphone. Please try again.",
    SecurityError:
      "Microphone recording requires localhost or a secure HTTPS connection.",
  };
  return new Error(messages[error?.name] || error?.message || "Unable to access the microphone.");
}

export function useAudioRecorder(onRecording) {
  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const wakeLockRef = useRef(null);
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);

  const stopTracks = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  const releaseWakeLock = () => {
    const lock = wakeLockRef.current;
    wakeLockRef.current = null;
    lock?.release().catch(() => {});
  };

  useEffect(() => () => {
    clearInterval(timerRef.current);
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
    stopTracks();
    releaseWakeLock();
  }, []);

  const start = async () => {
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      throw microphoneError({ name: "SecurityError" });
    }
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const knownInputs = devices.filter((device) => device.kind === "audioinput");
      if (devices.length && !knownInputs.length) {
        throw new DOMException("No audio input device", "NotFoundError");
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      streamRef.current = stream;
      recorderRef.current = recorder;
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        clearInterval(timerRef.current);
        stopTracks();
        setRecording(false);
        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });
        // Hold the wake lock through transcription too, not just recording —
        // a long answer can take a while to transcribe, and a screen that
        // locks mid-wait kills the in-flight request on iOS Safari.
        Promise.resolve(blob.size ? onRecording(blob) : null).finally(releaseWakeLock);
      };
      recorder.start(500);
      setSeconds(0);
      setRecording(true);
      timerRef.current = setInterval(() => setSeconds((value) => value + 1), 1000);
      try {
        wakeLockRef.current = (await navigator.wakeLock?.request("screen")) || null;
      } catch {
        // Wake Lock isn't supported or was denied — recording still works,
        // it's just more exposed to the screen locking mid-transcription.
      }
    } catch (error) {
      stopTracks();
      releaseWakeLock();
      throw microphoneError(error);
    }
  };

  const stop = () => recorderRef.current?.state === "recording" && recorderRef.current.stop();

  return { recording, seconds, start, stop };
}
