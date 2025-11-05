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
    thought?: string;
    step_type?: string;
    error?: string;
    answer?: string;
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
  saveToCache: (conversationKey: string) => void;
}

export const useConversation = (
  onError?: (error: string) => void,
  onMessageSent?: (threadId: string) => void  // 新增回调
): UseConversationReturn => {
  const [state, setState] = useState<ConversationState>({
    messages: [],
    loading: false,
    currentThreadId: null,
    error: null,
  });

  const abortControllerRef = useRef<AbortController | null>(null);

  /**
   * 发送消息并获取流式响应
   */
  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) {
      antdMessage.warning('请输入消息内容');
      return;
    }

    if (state.loading) {
      antdMessage.error('请求正在进行中，请等待完成');
      return;
    }

    // 创建新的 AbortController
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

    // 添加加载中的助手消息占位符
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
      const response = await fetch(API_ENDPOINTS.conversation.planStream, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
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
      let assistantContent = '';
      let backendFinalAnswer = '';
      let threadId = state.currentThreadId;
      const steps: any[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data: StepData = JSON.parse(line.slice(6));

              if (data.type === 'init') {
                // 初始化，保存 thread_id
                if (data.data.thread_id) {
                  threadId = data.data.thread_id;
                  setState((prev) => ({
                    ...prev,
                    currentThreadId: threadId,
                  }));
                }
              } else if (data.type === 'step' || data.type === 'thinking') {
                // 执行步骤
                steps.push(data.data);
                const stepContent = data.data.content || data.data.thought || '';
                
                if (stepContent) {
                  assistantContent += stepContent + '\n\n';
                  
                  // 实时更新助手消息
                  setState((prev) => {
                    const newMessages = [...prev.messages];
                    newMessages[loadingMessageIndex] = {
                      message: { role: 'assistant', content: assistantContent },
                      status: 'loading',
                    };
                    return { ...prev, messages: newMessages };
                  });
                }
              } else if (data.type === 'final' || data.type === 'finish') {
                // 最终答案（后端新增的最终事件）
                backendFinalAnswer = (data.data && (data.data.content || data.data.answer)) || backendFinalAnswer;
              } else if (data.type === 'complete') {
                // 完成
                // no-op: 仅作终止信号使用
              } else if (data.type === 'error') {
                throw new Error(data.data.error || '服务器返回错误');
              }
            } catch (parseError) {
              console.error('解析流数据失败:', parseError);
            }
          }
        }
      }

      // 更新最终消息状态
      setState((prev) => {
        const newMessages = [...prev.messages];
        newMessages[loadingMessageIndex] = {
          message: {
            role: 'assistant',
            // 优先展示后端提供的最终答案，其次展示累积的过程内容
            content: backendFinalAnswer || assistantContent || '处理完成，但没有返回内容。',
          },
          status: 'success',
        };
        return {
          ...prev,
          messages: newMessages,
          loading: false,
        };
      });

      // 通知外部 thread_id 已更新（用于同步保存）
      if (onMessageSent && threadId) {
        onMessageSent(threadId);
      }

    } catch (error: any) {
      // 处理中止请求
      if (error.name === 'AbortError') {
        setState((prev) => {
          const newMessages = [...prev.messages];
          newMessages[loadingMessageIndex] = {
            message: { role: 'assistant', content: '请求已中止' },
            status: 'error',
          };
          return {
            ...prev,
            messages: newMessages,
            loading: false,
            error: '请求已中止',
          };
        });
        return;
      }

      // 处理其他错误
      const errorMsg = error instanceof Error ? error.message : '未知错误';
      console.error('对话请求失败:', error);
      
      onError?.(errorMsg);
      antdMessage.error(`请求失败: ${errorMsg}`);

      setState((prev) => {
        const newMessages = [...prev.messages];
        newMessages[loadingMessageIndex] = {
          message: {
            role: 'assistant',
            content: `抱歉，请求失败: ${errorMsg}`,
          },
          status: 'error',
        };
        return {
          ...prev,
          messages: newMessages,
          loading: false,
          error: errorMsg,
        };
      });
    }
  }, [state.loading, state.currentThreadId, state.messages.length, onError]);

  /**
   * 清空消息历史
   */
  const clearMessages = useCallback(() => {
    setState((prev) => ({
      ...prev,
      messages: [],
      error: null,
    }));
  }, []);

  /**
   * 重置会话（清空消息和 thread_id）
   */
  const resetThread = useCallback(() => {
    setState((prev) => ({
      ...prev,
      messages: [],
      currentThreadId: null,
      error: null,
    }));
  }, []);

  /**
   * 中止当前请求
   */
  const abortRequest = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  /**
   * 加载历史消息（从缓存或后端恢复会话）
   */
  const loadMessages = useCallback((messages: MessageWithStatus[], threadId: string) => {
    setState((prev) => ({
      ...prev,
      messages,
      currentThreadId: threadId,
      error: null,
    }));
  }, []);

  /**
   * 保存当前会话到缓存（已禁用 - 所有数据由后端管理）
   */
  const saveToCache = useCallback((conversationKey: string) => {
    console.log('🚫 [生产模式] saveToCache 已禁用 - 数据由后端管理');
    console.log(`   conversationKey: ${conversationKey}`);
    // 不再保存到 localStorage
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
    saveToCache,
  };
};

