import React from 'react';
import { Button, Spin } from 'antd';
import { 
  ReloadOutlined, 
  CopyOutlined, 
  LikeOutlined, 
  DislikeOutlined 
} from '@ant-design/icons';
import { Bubble } from '@ant-design/x';
import { MessageRenderer } from './MessageRenderer';

interface MessageWithStatus {
  message: {
    role: 'user' | 'assistant';
    content: string;
  };
  status: 'success' | 'loading' | 'error';
}

interface MessageListProps {
  messages: MessageWithStatus[];
  loadingMessageStyle?: string;
}

/**
 * 消息列表组件
 * 负责渲染聊天消息列表
 */
export const MessageList: React.FC<MessageListProps> = ({ 
  messages, 
  loadingMessageStyle 
}) => {
  if (!messages?.length) {
    return null;
  }

  return (
    <Bubble.List
      items={messages.map((i) => ({
        ...i.message,
        content: (
          <MessageRenderer
            content={i.message.content}
            role={i.message.role}
            status={i.status}
          />
        ),
        classNames: {
          content: i.status === 'loading' ? loadingMessageStyle : '',
        },
        typing: i.status === 'loading' ? { 
          step: 5, 
          interval: 20, 
          suffix: <>💗</> 
        } : false,
      }))}
      style={{ 
        height: '100%', 
        paddingLeft: 'max(16px, calc(50% - 400px))',
        paddingRight: 'max(16px, calc(50% - 400px))',
        maxWidth: '800px',
        margin: '0 auto',
        textAlign: 'left'
      }}
      roles={{
        assistant: {
          placement: 'start',
          footer: (
            <div style={{ display: 'flex' }}>
              <Button type="text" size="small" icon={<ReloadOutlined />} />
              <Button type="text" size="small" icon={<CopyOutlined />} />
              <Button type="text" size="small" icon={<LikeOutlined />} />
              <Button type="text" size="small" icon={<DislikeOutlined />} />
            </div>
          ),
          loadingRender: () => <Spin size="small" />,
        },
        user: { placement: 'end' },
      }}
    />
  );
};
