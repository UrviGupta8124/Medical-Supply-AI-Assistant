"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff } from 'lucide-react';

interface SpeechToTextProps {
  onTranscript: (text: string) => void;
  className?: string;
  language?: string;
}

export default function SpeechToText({ onTranscript, className, language }: SpeechToTextProps) {
  const [isListening, setIsListening] = useState(false);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<any>(null);
  const isListeningRef = useRef<boolean>(false);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      setIsListening(true);
      isListeningRef.current = true;

      // We record in 2.5 second intervals to simulate real-time streaming.
      // Every 2.5 seconds, we stop the recorder, which fires the data, and start a new one.
      const recordChunk = () => {
        if (!streamRef.current || !isListeningRef.current) return;
        
        let mediaRecorder: MediaRecorder | null = null;
        try {
          mediaRecorder = new MediaRecorder(streamRef.current, { mimeType: 'audio/webm' });
        } catch (e) {
          mediaRecorder = new MediaRecorder(streamRef.current); // Fallback
        }
        
        mediaRecorder.ondataavailable = async (event) => {
          if (event.data.size > 0 && isListeningRef.current) {
            const formData = new FormData();
            formData.append('file', event.data, 'audio.webm');
            if (language) {
              formData.append('language', language);
            }
            try {
              const res = await fetch('http://localhost:5001/api/transcribe', {
                method: 'POST',
                body: formData,
              });
              if (res.ok) {
                const data = await res.json();
                if (data.text) onTranscript(data.text);
              }
            } catch (err) {
              console.error('Backend transcription error:', err);
            }
          }
        };

        mediaRecorder.start();
        
        setTimeout(() => {
          if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
          }
        }, 2500);
      };

      // Start the loop
      recordChunk();
      intervalRef.current = setInterval(() => {
        if (isListeningRef.current) recordChunk();
      }, 2500);

    } catch (err) {
      console.error('Microphone access denied or error:', err);
      alert('Microphone access denied. Please check your browser permissions.');
    }
  };

  const stopRecording = () => {
    setIsListening(false);
    isListeningRef.current = false;
    
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
  };

  const toggleListening = () => {
    if (isListening) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopRecording();
    };
  }, []);

  const baseClass = className || `p-3 rounded-full flex items-center justify-center transition-all shadow-md`;
  const listeningClass = isListening ? 'text-white bg-orange-500 hover:bg-orange-600 animate-pulse' : 'text-gray-700 bg-white border border-gray-200';
  const customListeningClass = isListening ? '!text-orange-500 animate-pulse' : '!text-red-500';

  return (
    <button
      type="button"
      onClick={toggleListening}
      className={className ? `${className} ${customListeningClass}` : `${baseClass} ${listeningClass}`}
      title={isListening ? "Stop Listening" : "Start Speech to Text"}
    >
      {isListening ? <MicOff size={20} /> : <Mic size={20} />}
    </button>
  );
}
