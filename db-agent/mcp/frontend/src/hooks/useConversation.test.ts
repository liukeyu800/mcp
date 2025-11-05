import { useState, useCallback, useRef } from 'react';
import { message as antdMessage } from 'antd';
import { API_ENDPOINTS } from '../config/api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface MessageWithStatus {
  message: Message;
  status: 'success' | 'loading' | 'error';
}

interface ConversationState {
  messages: MessageWithStatus[];
  loading: boolean;
  currentThreadId: string | null;
  error: string | null;
}

interface StepData {
  type: string;
  data: {
    thread_id?: string;
    content?: string;
  };
}

interface UseConversationReturn {
  messages: MessageWithStatus[];
  loading: boolean;
  currentThreadId: string | null;
  error: string | null;
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
  resetThread: () => void;
  abortRequest: () => void;
  loadMessages: (messages: MessageWithStatus[], threadId: string) => void;
}

/**
 * 测试版本的对话 Hook
 * 调用后端测试接口，使用后端返回的真实回答
 */
export const useConversationTest = (
  onError?: (error: string) => void,
  onMessageSent?: (threadId: string) => void
): UseConversationReturn => {
  const [state, setState] = useState<ConversationState>({
    messages: [],
    loading: false,
    currentThreadId: null,
    error: null,
  });

  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) {
      antdMessage.warning('请输入消息内容');
      return;
    }

    if (state.loading) {
      antdMessage.error('请求正在进行中，请等待完成');
      return;
    }

    abortControllerRef.current = new AbortController();

    // 添加用户消息
    const userMessage: MessageWithStatus = {
      message: { role: 'user', content },
      status: 'success',
    };

    setState((prev) => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      loading: true,
      error: null,
    }));

    const loadingMessageIndex = state.messages.length + 1;

    setState((prev) => ({
      ...prev,
      messages: [
        ...prev.messages,
        {
          message: { role: 'assistant', content: '' },
          status: 'loading' as const,
        },
      ],
    }));

    try {
      const response = await fetch(API_ENDPOINTS.conversation.testStream, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: content,
          thread_id: state.currentThreadId,
          max_steps: 12,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`API请求失败: ${response.status} ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('无法获取响应流');
      }

      const decoder = new TextDecoder();
      let threadId = state.currentThreadId;
      let backendResponse = '';
      
      // 读取后端流
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data: StepData = JSON.parse(line.slice(6));

              if (data.type === 'init' && data.data.thread_id) {
                threadId = data.data.thread_id;
                setState((prev) => ({ ...prev, currentThreadId: threadId }));
              }
              
              if (data.type === 'final' && data.data.content) {
                backendResponse = data.data.content;
              }
            } catch (parseError) {
              console.error('解析流数据失败:', parseError);
            }
          }
        }
      }

      // 使用后端返回的真实回答
      const assistantContent = backendResponse || '后端未返回回答';

      setState((prev) => {
        const newMessages = [...prev.messages];
        newMessages[loadingMessageIndex] = {
          message: { role: 'assistant', content: assistantContent },
          status: 'success',
        };
        return { ...prev, messages: newMessages, loading: false };
      });

      console.log('✅ [测试模式] 消息发送成功');
      console.log(`   用户消息: ${content.slice(0, 30)}...`);
      console.log(`   后端回答: ${backendResponse.slice(0, 50)}...`);
      console.log(`   threadId: ${threadId?.slice(0, 20)}...`);

      if (onMessageSent && threadId) {
        onMessageSent(threadId);
      }

    } catch (error: any) {
      if (error.name === 'AbortError') {
        setState((prev) => {
          const newMessages = [...prev.messages];
          newMessages[loadingMessageIndex] = {
            message: { role: 'assistant', content: '请求已中止' },
            status: 'error',
          };
          return { ...prev, messages: newMessages, loading: false, error: '请求已中止' };
        });
        return;
      }

      const errorMsg = error instanceof Error ? error.message : '未知错误';
      console.error('对话请求失败:', error);
      
      onError?.(errorMsg);
      antdMessage.error(`请求失败: ${errorMsg}`);

      setState((prev) => {
        const newMessages = [...prev.messages];
        newMessages[loadingMessageIndex] = {
          message: { role: 'assistant', content: `抱歉，请求失败: ${errorMsg}` },
          status: 'error',
        };
        return { ...prev, messages: newMessages, loading: false, error: errorMsg };
      });
    }
  }, [state.loading, state.currentThreadId, state.messages.length, onError]);

  const clearMessages = useCallback(() => {
    setState((prev) => ({ ...prev, messages: [], error: null }));
  }, []);

  const resetThread = useCallback(() => {
    setState((prev) => ({ ...prev, messages: [], currentThreadId: null, error: null }));
  }, []);

  const abortRequest = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  const loadMessages = useCallback((messages: MessageWithStatus[], threadId: string) => {
    console.log('📥 [测试模式] 加载历史消息');
    console.log(`   threadId: ${threadId?.slice(0, 20)}...`);
    console.log(`   消息数: ${messages.length}`);
    
    setState((prev) => ({ ...prev, messages, currentThreadId: threadId, error: null }));
  }, []);

  return {
    messages: state.messages,
    loading: state.loading,
    currentThreadId: state.currentThreadId,
    error: state.error,
    sendMessage,
    clearMessages,
    resetThread,
    abortRequest,
    loadMessages,
  };
};

