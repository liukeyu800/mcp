import {
  CloudUploadOutlined,
  CopyOutlined,
  DeleteOutlined,
  DislikeOutlined,
  EditOutlined,
  EllipsisOutlined,
  FileTextOutlined,
  LikeOutlined,
  PaperClipOutlined,
  PlusOutlined,
  QuestionCircleOutlined,
  ReloadOutlined,
  ShareAltOutlined,
  AudioOutlined,
  StopOutlined,
  PictureOutlined,
} from '@ant-design/icons';
import {
  Attachments,
  Bubble,
  Conversations,
  Prompts,
  Sender,
  Welcome,
  useXAgent,
  useXChat,
} from '@ant-design/x';
import { Avatar, Button, Flex, type GetProp, Space, Spin, message } from 'antd';
import { createStyles } from 'antd-style';
import dayjs from 'dayjs';
import React, { useEffect, useRef, useState } from 'react';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';
import { useImageOCR } from '../hooks/useImageOCR';
import { useConversation } from '../hooks/useConversation';
import { useConversationTest } from '../hooks/useConversation.test';  // 测试版本
import { useConversationManager } from '../hooks/useConversationManager';
import { MessageList } from '../components/MessageList';

// ========== 测试模式开关 ==========
// 设置为 true 启用测试模式（固定AI回答）
// 设置为 false 使用真实后端接口
const TEST_MODE = false;  // 👈 在这里切换测试/生产模式
// ==================================

type BubbleDataType = {
  role: string;
  content: string;
};

const DEFAULT_CONVERSATIONS_ITEMS = [
  {
    key: 'default-0',
    label: '在轨航天器轨道参数查询',
    group: '今天',
  },
  {
    key: 'default-1',
    label: '航天器遥测数据分析',
    group: '今天',
  },
  {
    key: 'default-2',
    label: '卫星姿态控制系统状态',
    group: '昨天',
  },
];

const HOT_TOPICS = {
  key: '1',
  label: '热门查询',
  children: [
    {
      key: '1-1',
      description: '在轨航天器轨道参数实时监测',
      icon: <span style={{ color: '#f93a4a', fontWeight: 700 }}>1</span>,
    },
    {
      key: '1-2',
      description: '卫星遥测数据异常分析',
      icon: <span style={{ color: '#ff6565', fontWeight: 700 }}>2</span>,
    },
    {
      key: '1-3',
      description: '航天器姿态控制系统状态查询',
      icon: <span style={{ color: '#ff8f1f', fontWeight: 700 }}>3</span>,
    },
    {
      key: '1-4',
      description: '空间碎片碰撞风险评估',
      icon: <span style={{ color: '#00000040', fontWeight: 700 }}>4</span>,
    },
    {
      key: '1-5',
      description: '卫星通信链路质量分析',
      icon: <span style={{ color: '#00000040', fontWeight: 700 }}>5</span>,
    },
  ],
};

const DESIGN_GUIDE = {
  key: '2',
  label: '数据分析指南',
  children: [
    {
      key: '2-1',
      description: '轨道参数分析方法',
      icon: <FileTextOutlined />,
    },
    {
      key: '2-2',
      description: '遥测数据处理流程',
      icon: <FileTextOutlined />,
    },
    {
      key: '2-3',
      description: '异常检测算法应用',
      icon: <FileTextOutlined />,
    },
    {
      key: '2-4',
      description: '预测模型构建指南',
      icon: <FileTextOutlined />,
    },
    {
      key: '2-5',
      description: '数据可视化最佳实践',
      icon: <FileTextOutlined />,
    },
  ],
};

const SENDER_PROMPTS: GetProp<typeof Prompts, 'items'> = [
  {
    key: '1',
    description: '查询卫星轨道参数',
  },
  {
    key: '2',
    description: '分析遥测数据异常',
  },
  {
    key: '3',
    description: '评估碰撞风险',
  },
  {
    key: '4',
    description: '监测姿态控制系统',
  },
];

const useStyle = createStyles(({ token, css }) => {
  return {
    layout: css`
      width: 100%;
      min-width: 1000px;
      height: 100vh;
      display: flex;
      background: ${token.colorBgContainer};
      font-family: AlibabaPuHuiTi, ${token.fontFamily}, sans-serif;
    `,
    // sider 样式
    sider: css`
      background: ${token.colorBgLayout}80;
      width: 280px;
      height: 100%;
      display: flex;
      flex-direction: column;
      padding: 0 12px;
      box-sizing: border-box;
    `,
    logo: css`
      display: flex;
      align-items: center;
      justify-content: start;
      padding: 0 24px;
      box-sizing: border-box;
      gap: 8px;
      margin: 24px 0;

      span {
        font-weight: bold;
        color: ${token.colorText};
        font-size: 16px;
      }
    `,
    addBtn: css`
      background: #1677ff0f;
      border: 1px solid #1677ff34;
      height: 40px;
    `,
    conversations: css`
      flex: 1;
      overflow-y: auto;
      margin-top: 12px;
      padding: 0;

      .ant-conversations-list {
        padding-inline-start: 0;
      }
    `,
    siderFooter: css`
      border-top: 1px solid ${token.colorBorderSecondary};
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    `,
    // chat list 样式
    chat: css`
      height: 100%;
      width: 100%;
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
      padding-block: ${token.paddingLG}px;
      gap: 16px;
    `,
    chatPrompt: css`
      .ant-prompts-label {
        color: #000000e0 !important;
      }
      .ant-prompts-desc {
        color: #000000a6 !important;
        width: 100%;
      }
      .ant-prompts-icon {
        color: #000000a6 !important;
      }
    `,
    chatList: css`
      flex: 1;
      overflow: auto;
    `,
    loadingMessage: css`
      background-image: linear-gradient(90deg, #ff6b23 0%, #af3cb8 31%, #53b6ff 89%);
      background-size: 100% 2px;
      background-repeat: no-repeat;
      background-position: bottom;
    `,
    placeholder: css`
      padding-top: 32px;
    `,
    // sender 样式
    sender: css`
      width: 100%;
      max-width: 700px;
      margin: 0 auto;
    `,
    speechButton: css`
      font-size: 18px;
      color: ${token.colorText} !important;
    `,
    senderPrompt: css`
      width: 100%;
      max-width: 700px;
      margin: 0 auto;
      color: ${token.colorText};
    `,
  };
});


const Independent: React.FC = () => {
  const { styles } = useStyle();

  // ==================== 会话管理 ====================
  const {
    conversations,
    currentConversation,
    createConversation,
    deleteConversation,
    switchConversation,
    updateConversationTitle,
    syncConversation,
    setCurrentConversation,
  } = useConversationManager();

  const [attachmentsOpen, setAttachmentsOpen] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<GetProp<typeof Attachments, 'items'>>([]);

  const [inputValue, setInputValue] = useState('');

  // 自定义语音识别
  const {
    isRecording,
    isProcessing,
    toggleRecording,
  } = useSpeechRecognition(
    (text) => {
      setInputValue(text);
    },
    (error) => {
      console.error('语音识别错误:', error);
    }
  );

  // 图片OCR识别
  const {
    isProcessing: isOCRProcessing,
    recognizeImage,
  } = useImageOCR(
    (text) => {
      // OCR识别成功后，将文字添加到输入框
      setInputValue((prev) => prev ? `${prev}\n${text}` : text);
    },
    (error) => {
      console.error('OCR识别错误:', error);
    }
  );

  /**
   * 🔔 使用本地后端API进行对话
   */

  // ==================== Runtime ====================
  // 根据 TEST_MODE 选择使用测试版本或生产版本
  const conversationHook = TEST_MODE ? useConversationTest : useConversation;
  
  const {
    messages,
    loading,
    currentThreadId,
    sendMessage,
    resetThread,
    abortRequest,
    loadMessages,
  } = conversationHook(
    (error) => {
      console.error('对话错误:', error);
    },
    // 消息发送完成回调 - 确保 thread_id 正确同步
    (threadId) => {
      if (currentConversation) {
        const conv = conversations.find((c) => c.key === currentConversation);
        console.log('\n💾 [消息发送] 同步会话数据到列表');
        console.log(`   会话: ${conv?.label || '未知'} (key: ${currentConversation})`);
        console.log(`   threadId: ${threadId.slice(0, 20)}...`);
        console.log(`   消息数: ${messages.length}`);
        console.log(`   🔄 检查是否需要更新会话列表中的 threadId\n`);
        
        // 只有当会话列表中的 threadId 为空或不同时才更新
        if (!conv?.threadId || conv.threadId !== threadId) {
          console.log(`   📝 更新会话 threadId: ${conv?.threadId ? conv.threadId.slice(0, 20) + '...' : 'null'} -> ${threadId.slice(0, 20)}...`);
          syncConversation(currentConversation, threadId);
        } else {
          console.log(`   ✅ 会话 threadId 已正确，无需更新`);
        }
      }
    }
  );

  // 显示当前模式
  useEffect(() => {
    if (TEST_MODE) {
      console.log('🧪 [测试模式] 已激活 - 使用固定AI回答');
    } else {
      console.log('🚀 [生产模式] 已激活 - 连接真实后端');
    }
  }, []);

  // ==================== Event ====================
  const onSubmit = async (val: string) => {
    if (!val) return;
    // 只发送消息，同步会话的工作由回调完成
    await sendMessage(val);
  };

  // ==================== Nodes ====================
  const chatSider = (
    <div className={styles.sider}>
      {/* 🌟 Logo */}
      <div className={styles.logo}>
        <img
          src="https://mdn.alipayobjects.com/huamei_iwk9zp/afts/img/A*eco6RrQhxbMAAAAAAAAAAAAADgCCAQ/original"
          draggable={false}
          alt="logo"
          width={24}
          height={24}
        />
        <span>在轨航天器数据分析系统</span>
      </div>

      {/* 🌟 添加会话 */}
      <Button
        onClick={() => {
          if (loading) {
            message.error(
              '消息正在请求中，请等待请求完成后再创建新会话或立即中止当前请求...',
            );
            return;
          }

          // 创建新会话
          createConversation();
          resetThread(); // 重置消息
        }}
        type="link"
        className={styles.addBtn}
        icon={<PlusOutlined />}
      >
        新建会话
      </Button>

      {/* 🌟 会话管理 */}
      <Conversations
        items={conversations}
        className={styles.conversations}
        activeKey={currentConversation || undefined}
        onActiveChange={async (val) => {
          // 获取会话信息用于日志
          const fromConv = conversations.find((c) => c.key === currentConversation);
          const toConv = conversations.find((c) => c.key === val);
          
          console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
          console.log('🔄 [会话切换] 开始切换');
          console.log(`   从: ${fromConv?.label || '无'} (key: ${currentConversation || '无'})`);
          // console.log(`   从的 threadId: ${fromConv?.threadId?.slice(0, 20) || '无'}...`);
          console.log(`   到: ${toConv?.label || '未知'} (key: ${val})`);
          // console.log(`   到的 threadId: ${toConv?.threadId?.slice(0, 20) || '无'}...`);
          // console.log(`   当前状态 threadId: ${currentThreadId?.slice(0, 20) || '无'}...`);
          console.log(`   当前消息数: ${messages.length}`);
          console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
          
          abortRequest(); // 中止当前请求
          
          // 🚫 不再保存到浏览器缓存，所有数据都在后端
          
          // 根据会话的 threadId 从后端加载
          if (toConv?.threadId) {
            console.log(`📡 [会话切换] 从后端加载: ${toConv.label}`);
            console.log(`   目标 threadId: ${toConv.threadId.slice(0, 20)}...`);
            
            const detail = await switchConversation(val);
            if (detail && detail.messages && detail.messages.length > 0) {
              console.log(`✅ [会话切换] 后端加载成功`);
              console.log(`   加载的 threadId: ${detail.threadId?.slice(0, 20) || 'undefined'}...`);
              console.log(`   消息数: ${detail.messages.length}`);
              console.log(`   第一条消息: ${detail.messages[0]?.message?.content?.slice(0, 20) || '无'}...`);
              loadMessages(detail.messages, detail.threadId);
            } else {
              console.log(`⚠️ [会话切换] 后端无数据，重置会话状态`);
              console.log(`   会话 threadId: ${toConv.threadId.slice(0, 20)}...`);
              // 虽然有 threadId，但后端没数据，重置到该 threadId
              resetThread();
              loadMessages([], toConv.threadId);
            }
          } else {
            // 新会话，没有 threadId
            console.log(`🆕 [会话切换] 新会话，重置状态: ${toConv?.label}`);
            resetThread();
          }
        }}
        groupable
        styles={{ item: { padding: '0 8px' } }}
        menu={(conversation) => ({
          items: [
            {
              label: '重命名',
              key: 'rename',
              icon: <EditOutlined />,
            },
            {
              label: '删除',
              key: 'delete',
              icon: <DeleteOutlined />,
              danger: true,
              onClick: async () => {
                await deleteConversation(conversation.key);
                // 删除后会自动切换到下一个会话
                if (conversation.key === currentConversation) {
                  resetThread();
                }
              },
            },
          ],
        })}
      />

      <div className={styles.siderFooter}>
        <Avatar size={24} />
        <Button type="text" icon={<QuestionCircleOutlined />} />
      </div>
    </div>
  );
  const chatList = (
    <div className={styles.chatList}>
      {messages?.length ? (
        /* 🌟 消息列表 */
        <MessageList 
          messages={messages} 
          loadingMessageStyle={styles.loadingMessage}
        />
      ) : (
        <Space
          direction="vertical"
          size={16}
          style={{ paddingInline: 'calc(calc(100% - 700px) /2)' }}
          className={styles.placeholder}
        >
          <Welcome
            variant="borderless"
            icon="https://mdn.alipayobjects.com/huamei_iwk9zp/afts/img/A*s5sNRo5LjfQAAAAAAAAAAAAADgCCAQ/fmt.webp"
            title="您好，我是在轨航天器数据分析助手"
            description="基于先进的AI技术，为您提供专业的航天器数据查询与分析服务~"
            extra={
              <Space>
                <Button icon={<ShareAltOutlined />} />
                <Button icon={<EllipsisOutlined />} />
              </Space>
            }
          />
          <Flex gap={16}>
            <Prompts
              items={[HOT_TOPICS]}
              styles={{
                list: { height: '100%' },
                item: {
                  flex: 1,
                  backgroundImage: 'linear-gradient(123deg, #e5f4ff 0%, #efe7ff 100%)',
                  borderRadius: 12,
                  border: 'none',
                },
                subItem: { padding: 0, background: 'transparent' },
              }}
              onItemClick={(info) => {
                onSubmit(info.data.description as string);
              }}
              className={styles.chatPrompt}
            />

            <Prompts
              items={[DESIGN_GUIDE]}
              styles={{
                item: {
                  flex: 1,
                  backgroundImage: 'linear-gradient(123deg, #e5f4ff 0%, #efe7ff 100%)',
                  borderRadius: 12,
                  border: 'none',
                },
                subItem: { background: '#ffffffa6' },
              }}
              onItemClick={(info) => {
                onSubmit(info.data.description as string);
              }}
              className={styles.chatPrompt}
            />
          </Flex>
        </Space>
      )}
    </div>
  );
  const senderHeader = (
    <Sender.Header
      title="上传文件"
      open={attachmentsOpen}
      onOpenChange={setAttachmentsOpen}
      styles={{ content: { padding: 0 } }}
    >
      <Attachments
        beforeUpload={async (file) => {
          // 如果是图片文件，自动进行OCR识别
          if (file.type.startsWith('image/')) {
            try {
              await recognizeImage(file);
              setAttachmentsOpen(false);
              return false; // 阻止自动上传
            } catch (error) {
              console.error('图片OCR识别失败:', error);
              return false;
            }
          }
          return false; // 其他文件类型暂不处理
        }}
        items={attachedFiles}
        onChange={(info) => setAttachedFiles(info.fileList)}
        placeholder={(type) =>
          type === 'drop'
            ? { title: '将文件拖拽到此处（支持图片OCR识别）' }
            : {
                icon: <CloudUploadOutlined />,
                title: '上传文件',
                description: '点击或拖拽文件到此区域，图片文件将自动进行OCR识别',
              }
        }
      />
    </Sender.Header>
  );
  const chatSender = (
    <>
      {/* 🌟 提示词 */}
      <Prompts
        items={SENDER_PROMPTS}
        onItemClick={(info) => {
          onSubmit(info.data.description as string);
        }}
        styles={{
          item: { padding: '6px 12px' },
        }}
        className={styles.senderPrompt}
      />
      {/* 🌟 输入框 */}
      <Sender
        value={inputValue}
        header={senderHeader}
        onSubmit={() => {
          onSubmit(inputValue);
          setInputValue('');
        }}
        onChange={setInputValue}
        onCancel={() => {
          abortRequest(); // 中止请求
        }}
        prefix={
          <Button
            type="text"
            icon={<PaperClipOutlined style={{ fontSize: 18 }} />}
            onClick={() => setAttachmentsOpen(!attachmentsOpen)}
          />
        }
        loading={loading}
        className={styles.sender}
        actions={(_, info) => {
          const { SendButton, LoadingButton } = info.components;
          return (
            <Flex gap={4}>
              <Button
                type="text"
                icon={isRecording ? <StopOutlined /> : <AudioOutlined />}
                onClick={toggleRecording}
                loading={isProcessing}
                className={styles.speechButton}
                style={{
                  color: isRecording ? '#ff4d4f' : undefined,
                  backgroundColor: isRecording ? '#fff2f0' : undefined,
                }}
                title={isRecording ? '停止录音' : '开始录音'}
              />
              {loading ? <LoadingButton type="default" /> : <SendButton type="primary" />}
            </Flex>
          );
        }}
        placeholder="请输入您的问题或使用 / 调用功能"
      />
    </>
  );

  // 自动保存消息到缓存
  // 🚫 已移除 saveToCache 相关逻辑 - 完全依赖后端数据

  // ==================== Render =================
  return (
    <div className={styles.layout}>
      {chatSider}

      <div className={styles.chat}>
        {chatList}
        {chatSender}
      </div>
    </div>
  );
};

export default Independent;