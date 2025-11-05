import { useState, useRef, useCallback } from 'react';
import { message } from 'antd';
import { SPEECH_SERVICE_URL } from '../config/api';

interface SpeechRecognitionState {
  isRecording: boolean;
  isProcessing: boolean;
  error: string | null;
}

interface UseSpeechRecognitionReturn {
  isRecording: boolean;
  isProcessing: boolean;
  error: string | null;
  startRecording: () => void;
  stopRecording: () => void;
  toggleRecording: () => void;
}

// 检查语音识别服务状态
const checkSpeechServiceStatus = async (): Promise<boolean> => {
  try {
    const response = await fetch(`${SPEECH_SERVICE_URL}/api/speech/status`, {
      method: 'GET',
    });
    
    if (response.ok) {
      const result = await response.json();
      return result.success && result.fireredasr_available && result.ffmpeg_available;
    }
    return false;
  } catch {
    return false;
  }
};

export const useSpeechRecognition = (
  onResult: (text: string) => void,
  onError?: (error: string) => void
): UseSpeechRecognitionReturn => {
  const [state, setState] = useState<SpeechRecognitionState>({
    isRecording: false,
    isProcessing: false,
    error: null,
  });

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const startRecording = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, error: null }));

      // 检查语音识别服务状态
      const serviceAvailable = await checkSpeechServiceStatus();
      if (!serviceAvailable) {
        throw new Error('语音识别服务不可用，请确保服务正在运行 (端口8001)');
      }

      // 获取麦克风权限
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        } 
      });
      
      streamRef.current = stream;
      audioChunksRef.current = [];

      // 创建MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
      });

      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        setState(prev => ({ ...prev, isProcessing: true }));
        
        try {
          // 创建音频Blob
          const audioBlob = new Blob(audioChunksRef.current, { 
            type: 'audio/webm;codecs=opus' 
          });

          // 转换为WAV格式（16kHz, 16-bit, mono）
          const wavBlob = await convertToWav(audioBlob);
          
          // 调用后端语音识别API
          const text = await callSpeechRecognitionAPI(wavBlob);
          
          if (text) {
            onResult(text);
            message.success('语音识别成功');
          } else {
            throw new Error('语音识别返回空结果');
          }
        } catch (error) {
          const errorMsg = error instanceof Error ? error.message : '语音识别失败';
          setState(prev => ({ ...prev, error: errorMsg }));
          onError?.(errorMsg);
          message.error(errorMsg);
        } finally {
          setState(prev => ({ ...prev, isProcessing: false }));
        }
      };

      mediaRecorder.start();
      setState(prev => ({ ...prev, isRecording: true }));
      message.info('开始录音...');

    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : '无法访问麦克风';
      setState(prev => ({ ...prev, error: errorMsg }));
      onError?.(errorMsg);
      message.error(errorMsg);
    }
  }, [onResult, onError]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && state.isRecording) {
      mediaRecorderRef.current.stop();
      setState(prev => ({ ...prev, isRecording: false }));
      message.info('录音结束，正在识别...');
    }

    // 停止所有音频轨道
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
  }, [state.isRecording]);

  const toggleRecording = useCallback(() => {
    if (state.isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [state.isRecording, startRecording, stopRecording]);

  return {
    isRecording: state.isRecording,
    isProcessing: state.isProcessing,
    error: state.error,
    startRecording,
    stopRecording,
    toggleRecording,
  };
};

// 转换音频格式为WAV
const convertToWav = async (audioBlob: Blob): Promise<Blob> => {
  return new Promise((resolve, reject) => {
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    const fileReader = new FileReader();

    fileReader.onload = async () => {
      try {
        const arrayBuffer = fileReader.result as ArrayBuffer;
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        
        // 重采样到16kHz
        const targetSampleRate = 16000;
        const resampledBuffer = await resampleAudioBuffer(audioBuffer, targetSampleRate);
        
        // 转换为WAV格式
        const wavBlob = audioBufferToWav(resampledBuffer);
        resolve(wavBlob);
      } catch (error) {
        reject(error);
      }
    };

    fileReader.onerror = () => reject(new Error('文件读取失败'));
    fileReader.readAsArrayBuffer(audioBlob);
  });
};

// 重采样音频缓冲区
const resampleAudioBuffer = async (audioBuffer: AudioBuffer, targetSampleRate: number): Promise<AudioBuffer> => {
  const offlineContext = new OfflineAudioContext(
    audioBuffer.numberOfChannels,
    Math.round(audioBuffer.duration * targetSampleRate),
    targetSampleRate
  );

  const source = offlineContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(offlineContext.destination);
  source.start();

  return await offlineContext.startRendering();
};

// 将AudioBuffer转换为WAV Blob
const audioBufferToWav = (audioBuffer: AudioBuffer): Blob => {
  const numberOfChannels = audioBuffer.numberOfChannels;
  const sampleRate = audioBuffer.sampleRate;
  const length = audioBuffer.length;
  
  const arrayBuffer = new ArrayBuffer(44 + length * numberOfChannels * 2);
  const view = new DataView(arrayBuffer);
  
  // WAV文件头
  const writeString = (offset: number, string: string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };
  
  writeString(0, 'RIFF');
  view.setUint32(4, 36 + length * numberOfChannels * 2, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, numberOfChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * numberOfChannels * 2, true);
  view.setUint16(32, numberOfChannels * 2, true);
  view.setUint16(34, 16, true);
  writeString(36, 'data');
  view.setUint32(40, length * numberOfChannels * 2, true);
  
  // 写入音频数据
  let offset = 44;
  for (let i = 0; i < length; i++) {
    for (let channel = 0; channel < numberOfChannels; channel++) {
      const sample = Math.max(-1, Math.min(1, audioBuffer.getChannelData(channel)[i]));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
      offset += 2;
    }
  }
  
  return new Blob([arrayBuffer], { type: 'audio/wav' });
};

// 调用后端语音识别API
const callSpeechRecognitionAPI = async (audioBlob: Blob): Promise<string> => {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'audio.wav');
  
  try {
    // 调用独立的语音识别服务 (端口8001)
    const response = await fetch(`${SPEECH_SERVICE_URL}/api/speech/recognize`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`语音识别请求失败: ${response.status} ${response.statusText} - ${errorText}`);
    }

    const result = await response.json();
    
    if (result.success && result.text) {
      return result.text;
    } else {
      throw new Error(result.error || result.message || '语音识别失败');
    }
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('无法连接到语音识别服务，请确保服务正在运行 (端口8001)');
    }
    throw error;
  }
};
