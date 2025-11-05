import React from 'react';
import { Button } from 'antd';
import { CopyOutlined } from '@ant-design/icons';

/**
 * 预处理 Markdown 内容
 * 处理多行代码块和特殊格式
 */
const preprocessMarkdown = (content: string): string => {
  // 处理多行代码块（跨段落的代码块）
  const lines = content.split('\n');
  let processedLines: string[] = [];
  let inCodeBlock = false;
  let codeBlockContent: string[] = [];
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    
    if (line.trim().startsWith('```')) {
      if (!inCodeBlock) {
        // 开始代码块
        inCodeBlock = true;
        codeBlockContent = [line];
      } else {
        // 结束代码块
        inCodeBlock = false;
        codeBlockContent.push(line);
        processedLines.push(codeBlockContent.join('\n'));
        codeBlockContent = [];
      }
    } else if (inCodeBlock) {
      // 在代码块内
      codeBlockContent.push(line);
    } else {
      // 普通行
      processedLines.push(line);
    }
  }
  
  // 如果还有未结束的代码块
  if (inCodeBlock && codeBlockContent.length > 0) {
    processedLines.push(codeBlockContent.join('\n'));
  }
  
  return processedLines.join('\n');
};

/**
 * 完整的 Markdown 解析器
 * 支持标题、段落、列表、代码块、表格、引用、链接、文本格式等
 */
export const formatAssistantMessage = (content: string): React.ReactNode => {
  if (!content) return content;

  // 预处理：处理多行代码块
  const processedContent = preprocessMarkdown(content);
  
  // 分割内容为段落
  const paragraphs = processedContent.split('\n\n');
  
  return paragraphs.map((paragraph, index) => {
    // 处理代码块
    if (paragraph.startsWith('```') && paragraph.endsWith('```')) {
      const codeContent = paragraph.slice(3, -3);
      const [language, ...codeLines] = codeContent.split('\n');
      const code = codeLines.join('\n');
      
      return (
        <div key={index} style={{ margin: '12px 0' }}>
          <div style={{
            background: '#f8f9fa',
            border: '1px solid #e9ecef',
            borderBottom: 'none',
            borderTopLeftRadius: '6px',
            borderTopRightRadius: '6px',
            padding: '8px 12px',
            fontSize: '12px',
            color: '#6c757d',
            fontWeight: 'bold',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <span>{language || 'code'}</span>
            <Button 
              type="text" 
              size="small" 
              icon={<CopyOutlined />}
              onClick={() => navigator.clipboard.writeText(code)}
              style={{ fontSize: '12px', height: '20px', padding: '0 4px' }}
            />
          </div>
          <pre style={{
            background: '#f8f9fa',
            padding: '12px',
            borderRadius: '0 0 6px 6px',
            margin: 0,
            overflow: 'auto',
            fontSize: '14px',
            fontFamily: 'Monaco, Consolas, "Courier New", monospace',
            border: '1px solid #e9ecef',
            borderTop: 'none',
            maxHeight: '400px'
          }}>
            <code>{code}</code>
          </pre>
        </div>
      );
    }

    // 处理行内代码
    if (paragraph.includes('`')) {
      const parts = paragraph.split('`');
      return (
        <p key={index} style={{ margin: '8px 0' }}>
          {parts.map((part, partIndex) => 
            partIndex % 2 === 1 ? (
              <code key={partIndex} style={{
                background: '#f0f0f0',
                padding: '2px 6px',
                borderRadius: '3px',
                fontSize: '13px',
                fontFamily: 'Monaco, Consolas, "Courier New", monospace'
              }}>
                {part}
              </code>
            ) : part
          )}
        </p>
      );
    }

    // 处理列表
    if (paragraph.includes('- ') || paragraph.includes('* ')) {
      const lines = paragraph.split('\n');
      const listItems = lines.filter(line => line.trim().startsWith('- ') || line.trim().startsWith('* '));
      if (listItems.length > 0) {
        return (
          <ul key={index} style={{ margin: '8px 0', paddingLeft: '20px' }}>
            {listItems.map((item, itemIndex) => (
              <li key={itemIndex} style={{ margin: '4px 0' }}>
                {item.replace(/^[-*]\s*/, '')}
              </li>
            ))}
          </ul>
        );
      }
    }

    // 处理数字列表
    if (paragraph.match(/^\d+\.\s/)) {
      const lines = paragraph.split('\n');
      const listItems = lines.filter(line => line.match(/^\d+\.\s/));
      if (listItems.length > 0) {
        return (
          <ol key={index} style={{ margin: '8px 0', paddingLeft: '20px' }}>
            {listItems.map((item, itemIndex) => (
              <li key={itemIndex} style={{ margin: '4px 0' }}>
                {item.replace(/^\d+\.\s*/, '')}
              </li>
            ))}
          </ol>
        );
      }
    }

    // 处理标题
    if (paragraph.startsWith('## ')) {
      return (
        <h3 key={index} style={{ 
          margin: '16px 0 8px 0', 
          fontSize: '16px', 
          fontWeight: 'bold',
          color: '#1890ff'
        }}>
          {paragraph.slice(3)}
        </h3>
      );
    }

    if (paragraph.startsWith('# ')) {
      return (
        <h2 key={index} style={{ 
          margin: '20px 0 12px 0', 
          fontSize: '18px', 
          fontWeight: 'bold',
          color: '#1890ff'
        }}>
          {paragraph.slice(2)}
        </h2>
      );
    }

    // 处理表格
    if (paragraph.includes('|') && paragraph.split('\n').length > 1) {
      const lines = paragraph.split('\n').filter(line => line.trim());
      if (lines.length >= 2) {
        const [header, ...rows] = lines;
        const headerCells = header.split('|').map(cell => cell.trim()).filter(cell => cell);
        const dataRows = rows.map(row => 
          row.split('|').map(cell => cell.trim()).filter(cell => cell)
        );
        
        return (
          <div key={index} style={{ margin: '12px 0', overflow: 'auto' }}>
            <table style={{
              width: '100%',
              borderCollapse: 'collapse',
              border: '1px solid #e8e8e8',
              borderRadius: '6px',
              overflow: 'hidden'
            }}>
              <thead>
                <tr style={{ background: '#fafafa' }}>
                  {headerCells.map((cell, cellIndex) => (
                    <th key={cellIndex} style={{
                      padding: '12px',
                      border: '1px solid #e8e8e8',
                      textAlign: 'left',
                      fontWeight: 'bold',
                      fontSize: '14px'
                    }}>
                      {cell}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dataRows.map((row, rowIndex) => (
                  <tr key={rowIndex} style={{ 
                    background: rowIndex % 2 === 0 ? '#fff' : '#fafafa' 
                  }}>
                    {row.map((cell, cellIndex) => (
                      <td key={cellIndex} style={{
                        padding: '12px',
                        border: '1px solid #e8e8e8',
                        fontSize: '14px'
                      }}>
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
    }

    // 处理引用块
    if (paragraph.startsWith('> ')) {
      const quoteText = paragraph.split('\n').map(line => 
        line.startsWith('> ') ? line.slice(2) : line
      ).join('\n');
      
      return (
        <blockquote key={index} style={{
          margin: '12px 0',
          padding: '12px 16px',
          background: '#f8f9fa',
          borderLeft: '4px solid #1890ff',
          borderRadius: '0 6px 6px 0',
          fontStyle: 'italic',
          color: '#666'
        }}>
          {quoteText}
        </blockquote>
      );
    }

    // 处理链接
    if (paragraph.includes('http')) {
      const urlRegex = /(https?:\/\/[^\s]+)/g;
      const parts = paragraph.split(urlRegex);
      return (
        <p key={index} style={{ margin: '8px 0' }}>
          {parts.map((part, partIndex) => 
            part.match(urlRegex) ? (
              <a 
                key={partIndex} 
                href={part} 
                target="_blank" 
                rel="noopener noreferrer"
                style={{ 
                  color: '#1890ff', 
                  textDecoration: 'underline',
                  wordBreak: 'break-all'
                }}
              >
                {part}
              </a>
            ) : part
          )}
        </p>
      );
    }

    // 处理粗体和斜体
    const formatText = (text: string): React.ReactNode => {
      // 处理粗体 **text** 或 __text__
      text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      text = text.replace(/__(.*?)__/g, '<strong>$1</strong>');
      
      // 处理斜体 *text* 或 _text_（避免与粗体冲突）
      text = text.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>');
      text = text.replace(/(?<!_)_([^_]+)_(?!_)/g, '<em>$1</em>');
      
      // 处理删除线 ~~text~~
      text = text.replace(/~~(.*?)~~/g, '<del>$1</del>');
      
      // 处理行内代码 `code`
      text = text.replace(/`([^`]+)`/g, '<code style="background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-family: Monaco, Consolas, \'Courier New\', monospace; font-size: 13px;">$1</code>');
      
      // 处理链接 [text](url)
      text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: #1890ff; text-decoration: underline;">$1</a>');
      
      // 处理图片 ![alt](url)
      text = text.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" style="max-width: 100%; height: auto; border-radius: 4px; margin: 8px 0;" />');
      
      // 处理高亮 ==text==
      text = text.replace(/==(.*?)==/g, '<mark style="background: #fff3cd; padding: 2px 4px; border-radius: 2px;">$1</mark>');
      
      // 处理下标 text~sub~
      text = text.replace(/~([^~]+)~/g, '<sub>$1</sub>');
      
      // 处理上标 text^sup^
      text = text.replace(/\^([^^]+)\^/g, '<sup>$1</sup>');
      
      return <span dangerouslySetInnerHTML={{ __html: text }} />;
    };

    // 普通段落
    return (
      <p key={index} style={{ 
        margin: '8px 0',
        textAlign: 'left',
        maxWidth: '100%'
      }}>
        {formatText(paragraph)}
      </p>
    );
  });
};

/**
 * 消息渲染器组件
 */
interface MessageRendererProps {
  content: string;
  role: 'user' | 'assistant';
  status?: 'success' | 'loading' | 'error';
}

export const MessageRenderer: React.FC<MessageRendererProps> = ({ 
  content, 
  role, 
  status = 'success' 
}) => {
  if (role === 'assistant') {
    return (
      <div style={{ 
        whiteSpace: 'pre-wrap', 
        lineHeight: '1.6',
        textAlign: 'left',
        maxWidth: '100%'
      }}>
        {formatAssistantMessage(content)}
      </div>
    );
  }
  
  return <span>{content}</span>;
};
