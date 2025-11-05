import { useState, useCallback, useEffect } from 'react';
import { message as antdMessage } from 'antd';
import { API_ENDPOINTS } from '../config/api';

/**
 * 根据时间戳获取时间分组
 */
const getTimeGroup = (timestamp: string | number): string => {
  const date = new Date(timestamp);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
  const targetDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  
  if (targetDate.getTime() === today.getTime()) {
    return '今天';
  } else if (targetDate.getTime() === yesterday.getTime()) {
    return '昨天';
  } else {
    return '更早';
  }
};


/**
 * 会话信息
 */
export interface ConversationInfo {
  key: string;              // 前端会话唯一标识
  label: string;            // 会话标题
  group?: string;           // 分组（今天、昨天等）
  threadId?: string;        // 后端 thread_id
  lastMessage?: string;     // 最后一条消息
  messageCount?: number;    // 消息数量
  createdAt?: number;       // 创建时间
  updatedAt?: number;       // 更新时间
}

/**
 * 会话详情（包含完整消息历史）
 */
export interface ConversationDetail {
  key: string;
  threadId: string;
  messages: any[];          // 消息历史
  state: any;               // 后端状态
}

interface UseConversationManagerReturn {
  conversations: ConversationInfo[];
  currentConversation: string | null;
  loading: boolean;
  
  // 会话操作
  createConversation: (label?: string) => ConversationInfo;
  deleteConversation: (key: string) => Promise<void>;
  switchConversation: (key: string) => Promise<ConversationDetail | null>;
  updateConversationTitle: (key: string, label: string) => void;
  
  // 会话同步
  syncConversation: (key: string, threadId: string, lastMessage?: string) => void;
  loadConversationHistory: () => Promise<void>;
  
  // 当前会话
  setCurrentConversation: (key: string | null) => void;
}

/**
 * 会话管理 Hook
 * 管理前端会话列表，并与后端 thread_id 同步
 */
export const useConversationManager = (): UseConversationManagerReturn => {
  const [conversations, setConversations] = useState<ConversationInfo[]>([]);
  const [currentConversation, setCurrentConversationState] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  /**
   * 从后端加载会话列表（纯后端数据，无本地缓存）
   */
  useEffect(() => {
    const loadConversations = async () => {
      try {
        console.log('🔄 [会话管理] 从后端加载会话列表...');
        const response = await fetch(API_ENDPOINTS.conversation.history);
        
        if (response.ok) {
          const data = await response.json();
          if (data.ok && data.conversations) {
            // 转换后端格式到前端格式
            const backendConversations: ConversationInfo[] = data.conversations.map((conv: any) => ({
              key: `conversation-${conv.thread_id}`,
              label: conv.title || `对话 ${conv.thread_id.slice(0, 8)}`,
              group: getTimeGroup(conv.updated_at || conv.created_at),
              createdAt: new Date(conv.created_at).getTime(),
              threadId: conv.thread_id,
            }));
            
            if (backendConversations.length > 0) {
              setConversations(backendConversations);
              setCurrentConversationState(backendConversations[0].key);
              
              console.log('✅ [会话管理] 后端加载成功');
              console.log(`   会话数: ${backendConversations.length}`);
              backendConversations.forEach(conv => {
                console.log(`   - ${conv.label} (${conv.threadId?.slice(0, 8)}...)`);
              });
            } else {
              // 后端没有会话，创建默认会话
              createDefaultConversation();
            }
          } else {
            console.log('⚠️ [会话管理] 后端返回数据格式错误');
            createDefaultConversation();
          }
        } else {
          console.log('⚠️ [会话管理] 后端加载失败，创建默认会话');
          createDefaultConversation();
        }
        
      } catch (error) {
        console.error('加载会话列表失败:', error);
        createDefaultConversation();
      }
    };
    
    const createDefaultConversation = () => {
      const defaultConversations: ConversationInfo[] = [
        {
          key: `conversation-${Date.now()}`,
          label: '新会话',
          group: '今天',
          createdAt: Date.now(),
        },
      ];
      setConversations(defaultConversations);
      setCurrentConversationState(defaultConversations[0].key);
      console.log('🆕 [会话管理] 创建默认会话');
    };
    
    loadConversations();
  }, []);


  /**
   * 创建新会话
   */
  const createConversation = useCallback((label?: string): ConversationInfo => {
    const now = Date.now();
    const newConversation: ConversationInfo = {
      key: `conversation-${now}`,
      label: label || `新会话 ${conversations.length + 1}`,
      group: '今天',
      createdAt: now,
      updatedAt: now,
    };

    setConversations((prev) => [newConversation, ...prev]);
    setCurrentConversationState(newConversation.key);

    return newConversation;
  }, [conversations.length]);

  /**
   * 删除会话
   */
  const deleteConversation = useCallback(async (key: string) => {
    const conversation = conversations.find((c) => c.key === key);
    
    // 如果有 thread_id，从后端删除
    if (conversation?.threadId) {
      try {
        const response = await fetch(API_ENDPOINTS.conversation.delete(conversation.threadId), {
          method: 'DELETE',
        });
        
        if (!response.ok) {
          console.error('后端删除会话失败');
        }
      } catch (error) {
        console.error('删除后端会话失败:', error);
      }
    }

    // 从前端列表删除
    setConversations((prev) => {
      const newList = prev.filter((c) => c.key !== key);
      
      // 如果删除的是当前会话，切换到第一个会话
      if (currentConversation === key && newList.length > 0) {
        setCurrentConversationState(newList[0].key);
      }
      
      return newList;
    });

  }, [conversations, currentConversation]);

  /**
   * 切换会话
   */
  const switchConversation = useCallback(async (key: string): Promise<ConversationDetail | null> => {
    setCurrentConversationState(key);
    
    const conversation = conversations.find((c) => c.key === key);
    if (!conversation) {
      return null;
    }

    // 如果有 thread_id，尝试从后端加载（可选功能）
    if (conversation.threadId) {
      setLoading(true);
      try {
        const response = await fetch(API_ENDPOINTS.conversation.detail(conversation.threadId));
        
        if (response.ok) {
          const data = await response.json();
          
          if (data.ok) {
            // 优先使用final_answer，如果没有则使用过滤后的messages
            const backendMessages = data.state?.messages || [];
            
            // 如果有final_answer，确保它被包含在消息中
            let convertedMessages = backendMessages.map((msg: any) => ({
              message: {
                role: msg.role,
                content: msg.content
              },
              status: 'success' as const
            }));
            
            // 如果有final_answer且最后一条消息不是它，添加final_answer
            if (data.final_answer) {
              const lastMessage = convertedMessages[convertedMessages.length - 1];
              if (!lastMessage || 
                  lastMessage.message.role !== 'assistant' || 
                  lastMessage.message.content !== data.final_answer) {
                convertedMessages.push({
                  message: {
                    role: 'assistant',
                    content: data.final_answer
                  },
                  status: 'success' as const
                });
              }
            }
            
            console.log('✅ [会话管理] 从后端加载成功');
            console.log(`   过滤后消息数: ${backendMessages.length}`);
            console.log(`   最终消息数: ${convertedMessages.length}`);
            if (data.final_answer) {
              console.log(`   最终答案: ${data.final_answer.substring(0, 50)}...`);
            }
            
            const detail: ConversationDetail = {
              key,
              threadId: conversation.threadId,
              messages: convertedMessages,
              state: data.state,
            };
            
            return detail;
          }
        } else if (response.status === 404) {
          console.log('⚠️ [会话管理] 后端未找到此会话');
        }
      } catch (error) {
        console.log('⚠️ [会话管理] 后端加载失败:', error);
      } finally {
        setLoading(false);
      }
    }

    return null;
  }, [conversations]);

  /**
   * 更新会话标题
   */
  const updateConversationTitle = useCallback((key: string, label: string) => {
    setConversations((prev) =>
      prev.map((c) => (c.key === key ? { ...c, label, updatedAt: Date.now() } : c))
    );
  }, []);

  /**
   * 同步会话信息（在发送消息后调用）
   */
  const syncConversation = useCallback(
    (key: string, threadId: string, lastMessage?: string) => {
      setConversations((prev) =>
        prev.map((c) =>
          c.key === key
            ? {
                ...c,
                threadId,
                lastMessage,
                updatedAt: Date.now(),
                messageCount: (c.messageCount || 0) + 1,
              }
            : c
        )
      );
    },
    []
  );

  /**
   * 手动刷新会话历史（从后端重新加载）
   */
  const loadConversationHistory = useCallback(async () => {
    setLoading(true);
    try {
      console.log('🔄 [会话管理] 手动刷新会话历史...');
      const response = await fetch(API_ENDPOINTS.conversation.history);
      
      if (response.ok) {
        const data = await response.json();
        
        if (data.ok && data.conversations) {
          // 转换后端格式到前端格式
          const backendConversations: ConversationInfo[] = data.conversations.map((conv: any) => ({
            key: `conversation-${conv.thread_id}`,
            label: conv.title || `对话 ${conv.thread_id.slice(0, 8)}`,
            group: getTimeGroup(conv.updated_at || conv.created_at),
            createdAt: new Date(conv.created_at).getTime(),
            threadId: conv.thread_id,
          }));
          
          setConversations(backendConversations);
          
          console.log('✅ [会话管理] 手动刷新完成');
          console.log(`   会话数: ${backendConversations.length}`);
          backendConversations.forEach(conv => {
            console.log(`   - ${conv.label} (${conv.threadId?.slice(0, 8)}...)`);
          });
          
          antdMessage.success(`已刷新会话列表，共 ${backendConversations.length} 个会话`);
        } else {
          console.log('⚠️ [会话管理] 后端返回数据格式错误');
          antdMessage.warning('刷新失败：数据格式错误');
        }
      } else {
        console.error('刷新会话历史失败:', response.status);
        antdMessage.error('刷新会话历史失败');
      }
    } catch (error) {
      console.error('刷新会话历史失败:', error);
      antdMessage.error('刷新会话历史失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const setCurrentConversation = useCallback((key: string | null) => {
    setCurrentConversationState(key);
  }, []);

  return {
    conversations,
    currentConversation,
    loading,
    
    createConversation,
    deleteConversation,
    switchConversation,
    updateConversationTitle,
    
    syncConversation,
    loadConversationHistory,
    
    setCurrentConversation,
  };
};

