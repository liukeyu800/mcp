import { useState, useCallback } from 'react';
import { message } from 'antd';
import { API_ENDPOINTS } from '../config/api';

interface ImageOCRState {
  isProcessing: boolean;
  error: string | null;
}

interface UseImageOCRReturn {
  isProcessing: boolean;
  error: string | null;
  recognizeImage: (file: File) => Promise<string>;
}

export const useImageOCR = (
  onResult?: (text: string) => void,
  onError?: (error: string) => void
): UseImageOCRReturn => {
  const [state, setState] = useState<ImageOCRState>({
    isProcessing: false,
    error: null,
  });

  const recognizeImage = useCallback(async (file: File): Promise<string> => {
    try {
      setState({ isProcessing: true, error: null });
      message.loading('正在识别图片文字...', 0);

      // 创建FormData
      const formData = new FormData();
      formData.append('image', file);

      // 调用OCR服务
      const response = await fetch(API_ENDPOINTS.ocr.recognize, {
        method: 'POST',
        body: formData,
      });

      message.destroy();

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`OCR识别失败: ${response.status} ${response.statusText} - ${errorText}`);
      }

      const result = await response.json();

      if (result.success) {
        const text = result.text || '';
        if (text) {
          message.success(`识别成功，共${result.line_count || 0}行文字`);
          onResult?.(text);
        } else {
          message.warning('未识别到文字内容');
        }
        setState({ isProcessing: false, error: null });
        return text;
      } else {
        throw new Error(result.error || result.message || 'OCR识别失败');
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'OCR识别失败';
      setState({ isProcessing: false, error: errorMsg });
      onError?.(errorMsg);
      message.error(errorMsg);
      throw error;
    }
  }, [onResult, onError]);

  return {
    isProcessing: state.isProcessing,
    error: state.error,
    recognizeImage,
  };
};

