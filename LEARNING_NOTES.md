# LLM App 学习笔记

这个文件用来记录我们在构建项目时学到的知识、做过的设计决定，以及踩过的小坑。

目标不是写成正式文档，而是保留一条清晰的学习轨迹：以后回头看时，你能知道每一步为什么这样做。

## 1. 项目目标

我们正在做一个个人使用的 LLM 客户端。它可以使用我们自己的 API Key，请求不同模型厂商，例如：

- OpenAI / GPT
- Google / Gemini
- Anthropic / Claude

长期方向是：

- 先做一个普通聊天客户端。
- 支持多个模型 provider。
- 支持流式输出 streaming。
- 支持会话历史。
- 之后逐步演进成本地 Agent，让它能安全地读文件、改文件、运行命令。

## 2. 总体架构

项目分成两部分：

```text
frontend/  React + TypeScript 前端界面
backend/   Django API 后端服务
```

一次聊天请求的大致流程是：

```text
用户输入消息
  -> React 发送统一格式的请求
  -> Django 接收 /api/chat/
  -> Django 根据 provider 选择对应 adapter
  -> adapter 请求 OpenAI/Gemini/Claude
  -> Django 返回 assistant 消息
  -> React 把回复渲染到页面上
```

核心思想：

```text
前端不要关心每家模型厂商的 API 差异。
前端只发送一种统一格式。
后端负责把统一格式转换成不同厂商需要的格式。
```

## 3. 为什么 API Key 应该放在后端

一开始我们支持前端输入 API Key，后面改成优先从 `backend/.env` 读取。

原因是：

- 前端代码运行在浏览器里。
- 浏览器里的内容都可以被用户检查到。
- 真正的 API Key 不应该打包进前端代码。
- 通过后端代理请求，可以让 API Key 留在服务端。

当前学习项目同时支持两种方式：

- 默认使用 `backend/.env` 里的 key。
- 前端可以临时输入 API Key 作为 override，用于测试。

目前支持的环境变量名：

```text
OPENAI_API_KEY / OPENAI_KEY
GEMINI_API_KEY / GOOGLE_API_KEY
ANTHROPIC_API_KEY / CLAUDE_API_KEY
```

## 4. 前端学到的基础概念

前端用 React 的 state 保存页面状态。

当前主要状态有：

```ts
provider      // 当前选择 OpenAI / Gemini / Claude
model         // 当前模型名
apiKey        // 可选的前端临时 API Key override
input         // 输入框内容
systemPrompt  // 系统提示词
messages      // 当前聊天消息列表
isLoading     // 是否正在等待模型回复
error         // 错误信息
```

关键理解：

```text
state 改变 -> React 重新渲染 UI
```

主组件文件是：

```text
frontend/src/App.tsx
```

它负责：

- provider 选择
- model 输入
- API Key override 输入
- system prompt 输入
- 消息列表展示
- 发送消息
- loading 状态
- 错误状态

## 5. TypeScript 学到的基础概念

TypeScript 用来描述数据的形状。

例如：

```ts
export type Provider = "openai" | "gemini" | "anthropic";

export type ChatMessage = {
  role: "system" | "user" | "assistant";
  content: string;
};
```

这带来的好处：

- `provider` 只能是允许的三个字符串之一。
- `role` 只能是 `system`、`user`、`assistant` 之一。
- 很多错误可以在写代码时就被编辑器或编译器发现。

前后端通信相关的类型定义在：

```text
frontend/src/types/chat.ts
```

## 6. 后端学到的基础概念

Django 后端现在提供这个接口：

```text
POST /api/chat/
```

主要入口文件是：

```text
backend/chat/views.py
```

它负责：

- 只接受 POST 请求。
- 解析 JSON 请求体。
- 校验 `provider`、`model`、`messages`。
- 从请求或 `.env` 中获取 API Key。
- 根据 provider 选择对应 adapter。
- 返回统一格式的 assistant 消息。

注意：

如果你直接在浏览器地址栏打开 `/api/chat/`，浏览器会发送 `GET` 请求，所以后端会返回：

```text
Only POST is supported.
```

这是正常的。真正的聊天请求应该从前端页面通过 `fetch()` 发出。

## 7. Adapter Pattern

每家模型厂商要求的请求格式不一样。

为了避免前端到处写 provider 判断，我们让后端 adapter 负责转换格式。

adapter 文件：

```text
backend/chat/providers/openai.py
backend/chat/providers/gemini.py
backend/chat/providers/anthropic.py
```

例子：

- OpenAI 使用 Responses API。
- Gemini 使用 `contents`，而且 assistant 角色叫 `model`。
- Anthropic / Claude 把 system prompt 放在顶层 `system` 字段里。

这种做法叫：

```text
Adapter Pattern
```

也就是：

```text
项目内部使用统一接口。
每个外部服务用一个 adapter 适配自己的特殊格式。
```

## 8. HTTP Helper

文件：

```text
backend/chat/providers/http.py
```

里面封装了通用的 `POST JSON` 请求逻辑。

这样 OpenAI、Gemini、Claude 三个 adapter 不需要重复写同样的 HTTP 请求代码。

这是一个小型的代码复用例子：

```text
当重复已经真实出现时，再抽出公共函数。
```

## 9. Node 和 Vite 环境问题

我们遇到过一个很典型的前端环境问题：

- 新版本 Vite 需要较新的 Node。
- 机器里原本有旧的 `/usr/local/bin/node`。
- Homebrew 安装的 `node@22` 在 `/opt/homebrew/opt/node@22/bin/node`。

后来我们把 shell path 调整好，让默认 Node 指向 Node 22。

常用检查命令：

```bash
which node
node -v
which npm
npm -v
```

经验：

```text
前端工具链出怪问题时，先检查 Node 版本和 node 路径。
```

## 10. Vite 和 TypeScript 更新

升级到新版 Vite / TypeScript 后，我们调整了：

```text
frontend/tsconfig.json
frontend/src/vite-env.d.ts
```

重要改动：

- `moduleResolution` 改成了 `Bundler`。
- 新增 `vite-env.d.ts`，让 TypeScript 理解 Vite 项目里的 CSS import 等类型。

这是现代前端工具链里很常见的配置。

## 11. 前端布局优化

最早的 UI 更像普通网页，容易出现全局滚动。

我们把它改成了更像应用的布局：

- 左侧设置栏
- 顶部聊天信息栏
- 中间消息列表
- 底部输入区
- 桌面端不再使用全局页面滚动
- 只有消息列表区域滚动

主要改动文件：

```text
frontend/src/App.tsx
frontend/src/styles.css
```

关键 CSS 思路：

```css
body {
  overflow: hidden;
}

.messages {
  overflow-y: auto;
}
```

这样页面更像 ChatGPT / Codex 这类工具，而不是普通网页。

## 12. OpenAI 429 Quota 错误

我们看到过这个错误：

```text
HTTP 429 insufficient_quota
```

含义：

```text
代码已经成功请求到了 OpenAI。
但是这个 API Key 对应的账户或项目没有可用额度。
```

常见原因：

- 没有绑定 API billing。
- 免费额度用完。
- 项目 budget 到上限。
- API Key 属于没有额度的 project。
- OpenAI API 和 ChatGPT 订阅不是同一个东西。

重要结论：

```text
ChatGPT Plus / Pro 订阅不等于 OpenAI API 额度。
```

这是账号计费问题，不是代码问题。

## 13. Streaming 流式输出

之前的行为是：

```text
发送消息 -> 等模型完整回复 -> 一次性显示
```

我们把 OpenAI 改成了 streaming：

```text
发送消息 -> assistant 气泡马上出现 -> 文本随着模型生成逐步更新
```

这就是流式输出。

### 13.1 后端做了什么

新增接口：

```text
POST /api/chat/stream/
```

相关文件：

```text
backend/chat/urls.py
backend/chat/views.py
backend/chat/providers/openai.py
```

Django 使用：

```py
StreamingHttpResponse
```

普通 `JsonResponse` 是一次性返回完整 JSON。

`StreamingHttpResponse` 可以边生成边返回内容。

### 13.2 OpenAI 上游 streaming

OpenAI Responses API 开启 streaming 的方式是：

```json
{
  "stream": true
}
```

OpenAI 返回的是 SSE，也就是 Server-Sent Events。

我们在后端解析事件，只关心这种事件：

```text
response.output_text.delta
```

其中的 `delta` 就是模型新生成的一小段文本。

### 13.3 前端做了什么

新增函数：

```text
frontend/src/api/chat.ts
```

```ts
streamChatMessage(request, onChunk)
```

它使用浏览器的：

```ts
response.body.getReader()
```

来一段段读取后端返回的文本。

### 13.4 React 如何显示 streaming

核心 UI 技巧：

```text
1. 用户消息先加入 messages
2. 立刻追加一条空的 assistant 消息
3. 每收到一个 chunk，就更新最后一条 assistant 消息
```

代码思路：

```ts
setMessages((currentMessages) => {
  const updatedMessages = [...currentMessages];
  const lastMessage = updatedMessages[updatedMessages.length - 1];

  updatedMessages[updatedMessages.length - 1] = {
    ...lastMessage,
    content: lastMessage.content + chunk,
  };

  return updatedMessages;
});
```

这体现了 React 的一个重要原则：

```text
不要直接修改原数组。
创建新数组，然后 setState。
```

### 13.5 为什么先只做 OpenAI

不同 provider 的 streaming 格式不同。

为了学习更清晰，我们先只实现 OpenAI：

- OpenAI streaming 已经接通。
- Gemini / Claude 暂时还走普通非 streaming 请求。
- 等理解机制后，再分别适配其他 provider。

本阶段学到的概念：

- Django `StreamingHttpResponse`
- HTTP streaming
- 前端 `ReadableStream`
- React 如何增量更新最后一条 assistant 消息
- 不同 provider 的 streaming 格式为什么不一样
