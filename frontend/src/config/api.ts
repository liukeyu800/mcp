/**
 * API 配置文件
 * 集中管理所有后端API地址
 */

// 后端API基础地址
export const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

// OCR服务地址
export const OCR_SERVICE_URL = process.env.REACT_APP_OCR_SERVICE_URL || 'http://localhost:8002';

// 语音识别服务地址
export const SPEECH_SERVICE_URL = process.env.REACT_APP_SPEECH_SERVICE_URL || 'http://localhost:8001';

// API端点
export const API_ENDPOINTS = {
  // 对话相关
  conversation: {
    plan: `${API_BASE_URL}/api/conversation/plan`,
    planStream: `${API_BASE_URL}/api/conversation/plan/stream`,
    history: `${API_BASE_URL}/api/conversation/history`,
    detail: (threadId: string) => `${API_BASE_URL}/api/conversation/${threadId}`,
    delete: (threadId: string) => `${API_BASE_URL}/api/conversation/${threadId}`,
    
    // 测试接口（简化模式，不使用ReAct）
    testSimple: `${API_BASE_URL}/api/conversation/test/simple`,
    testStream: `${API_BASE_URL}/api/conversation/test/stream`,
  },
  
  // 工具相关
  tools: {
    list: `${API_BASE_URL}/api/tools`,
    categories: `${API_BASE_URL}/api/tools/categories`,
    execute: `${API_BASE_URL}/api/tools/execute`,
  },
  
  // 数据库相关
  database: {
    tables: `${API_BASE_URL}/api/database/tables`,
    tableDetail: (tableName: string) => `${API_BASE_URL}/api/database/tables/${tableName}`,
    query: `${API_BASE_URL}/api/database/query`,
    sample: (tableName: string) => `${API_BASE_URL}/api/database/tables/${tableName}/sample`,
  },
  
  // OCR相关
  ocr: {
    recognize: `${OCR_SERVICE_URL}/api/ocr/recognize`,
  },
  
  // 语音识别相关
  speech: {
    recognize: `${SPEECH_SERVICE_URL}/api/speech/recognize`,
  },
  
  // 系统相关
  system: {
    info: `${API_BASE_URL}/api/system/info`,
    prompt: `${API_BASE_URL}/api/system/prompt`,
    health: `${API_BASE_URL}/health`,
  },
};

export default API_ENDPOINTS;

