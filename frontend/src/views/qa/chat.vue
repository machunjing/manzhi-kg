<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { askQuestion, qaSessions, getDocument, DISEASES } from '@/api'

interface Msg {
  id: number
  role: 'user' | 'assistant'
  text?: string
  result?: any
  pending?: boolean
  openSteps?: boolean
  feedback?: 'up' | 'down' | ''
}

const sessions = ref<any[]>(qaSessions.map((s) => ({ ...s })))
const activeSession = ref('')
const messages = ref<Msg[]>([])
const input = ref('')
const sending = ref(false)
const scrollBox = ref<HTMLElement>()
const evidenceTab = ref('text')
const activeResult = ref<any>(null)
const docDrawer = reactive({ visible: false, doc: {} as any })

const presets = [
  { q: '2型糖尿病与高血压有哪些关联？', tag: '疾病关联' },
  { q: '高血压的主要危险因素有哪些？', tag: '危险因素' },
  { q: '血脂异常与冠心病之间有什么联系？', tag: '疾病关联' },
  { q: '糖尿病常见并发症有哪些？', tag: '并发症' }
]

let msgId = 1

onMounted(() => {
  newChat()
})

function newChat() {
  activeSession.value = ''
  messages.value = []
  activeResult.value = null
  input.value = ''
}

function openSession(s: any) {
  activeSession.value = s.id
  messages.value = []
  activeResult.value = null
  input.value = s.title
  ElMessage.info('已载入历史会话标题，可重新提问以生成新的检索过程（演示环境不缓存完整对话）')
}

async function delSession(s: any) {
  try {
    await ElMessageBox.confirm(`删除会话「${s.title}」？删除后不可恢复。`, '删除历史对话', { type: 'warning' })
    sessions.value = sessions.value.filter((x) => x.id !== s.id)
    if (activeSession.value === s.id) newChat()
    ElMessage.success('会话已删除')
  } catch {
    /* cancelled */
  }
}

async function send(text?: string) {
  const q = (text ?? input.value).trim()
  if (!q) return ElMessage.warning('请输入问题')
  if (sending.value) return
  sending.value = true
  messages.value.push({ id: msgId++, role: 'user', text: q })
  const placeholder: Msg = { id: msgId++, role: 'assistant', pending: true, openSteps: false }
  messages.value.push(placeholder)
  input.value = ''
  scrollToBottom()

  const res = await askQuestion(q)
  const idx = messages.value.findIndex((m) => m.id === placeholder.id)
  messages.value[idx] = { ...placeholder, pending: false, result: res }
  activeResult.value = res
  evidenceTab.value = 'text'
  sending.value = false
  scrollToBottom()
}

function scrollToBottom() {
  nextTick(() => {
    if (scrollBox.value) scrollBox.value.scrollTop = scrollBox.value.scrollHeight
  })
}

function copyAnswer(m: Msg) {
  const text = m.result?.intent?.paragraphs?.join('\n\n') || ''
  navigator.clipboard?.writeText(text)
  ElMessage.success('回答已复制到剪贴板')
}

async function regenerate(m: Msg) {
  const prev = messages.value[messages.value.indexOf(m) - 1]
  if (!prev?.text) return
  ElMessage.info('正在重新生成…')
  await send(prev.text)
}

function feedback(m: Msg, v: 'up' | 'down') {
  m.feedback = v
  ElMessage.success(v === 'up' ? '感谢反馈，已记录为「有帮助」' : '已记录为「无帮助」，将用于优化检索策略')
}

function openDoc(doc: any) {
  docDrawer.doc = getDocument(doc.id) || doc
  docDrawer.visible = true
}

function viewEvidence(res: any) {
  activeResult.value = res
  evidenceTab.value = 'text'
  ElMessage.success('证据面板已更新为当前回答的引用来源')
}

const currentAnswer = computed(() => activeResult.value)
const allChunks = computed(() => activeResult.value?.chunks || [])
const allCitations = computed(() => activeResult.value?.citations || [])
</script>

<template>
  <div class="qa-page">
    <!-- 左：会话列表 -->
    <aside class="qa-side">
      <el-button type="primary" class="new-btn" @click="newChat">
        <el-icon><Plus /></el-icon>新建对话
      </el-button>
      <div class="side-label">最近问答历史</div>
      <div class="session-list">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="session"
          :class="{ active: activeSession === s.id }"
          @click="openSession(s)"
        >
          <div class="s-body">
            <div class="s-title">{{ s.title }}</div>
            <div class="s-meta">{{ s.createdAt }} · {{ s.rounds }} 轮</div>
          </div>
          <el-icon class="s-del" @click.stop="delSession(s)"><Delete /></el-icon>
        </div>
      </div>
      <div class="side-foot">
        <div class="sf-line">当前为演示模式</div>
        <div class="sf-line">未接入真实 GLM-4 接口</div>
      </div>
    </aside>

    <!-- 中：对话区 -->
    <section class="qa-main">
      <div class="qa-head">
        <div class="head-brand">
          <div class="brand-badge"><el-icon :size="16"><ChatDotRound /></el-icon></div>
          <div>
            <div class="hb-title">慢知智能助手</div>
            <div class="hb-desc">基于慢性病知识图谱与检索增强生成技术，为用户提供可追溯的健康知识服务</div>
          </div>
        </div>
        <el-tag size="small" type="warning" effect="light" round>模拟问答 · 非真实模型</el-tag>
      </div>

      <div ref="scrollBox" class="chat-scroll">
        <!-- 欢迎区 -->
        <div v-if="!messages.length" class="welcome">
          <div class="w-icon">
            <svg width="34" height="34" viewBox="0 0 24 24" fill="none">
              <path d="M12 3v18M3 12h18" stroke="#2563EB" stroke-width="1.4" stroke-linecap="round" />
              <circle cx="12" cy="12" r="3" fill="#2563EB" />
              <circle cx="12" cy="3" r="1.6" fill="#93B4F5" />
              <circle cx="12" cy="21" r="1.6" fill="#93B4F5" />
              <circle cx="3" cy="12" r="1.6" fill="#93B4F5" />
              <circle cx="21" cy="12" r="1.6" fill="#93B4F5" />
            </svg>
          </div>
          <div class="w-title">你好，我是慢知智能助手</div>
          <div class="w-desc">可以问我慢性病之间的关联、危险因素、并发症与监测指标。回答会附带文献引用与图谱证据路径。</div>
          <div class="presets">
            <div v-for="p in presets" :key="p.q" class="preset" @click="send(p.q)">
              <span class="p-tag">{{ p.tag }}</span>
              <span class="p-q">{{ p.q }}</span>
              <el-icon class="p-arrow"><Right /></el-icon>
            </div>
          </div>
        </div>

        <!-- 消息 -->
        <div v-for="m in messages" :key="m.id" class="msg" :class="m.role">
          <div v-if="m.role === 'user'" class="u-row">
            <div class="u-bubble">{{ m.text }}</div>
            <el-avatar :size="30" class="u-avatar">马</el-avatar>
          </div>

          <div v-else class="a-row">
            <el-avatar :size="30" class="a-avatar"><el-icon :size="16"><MagicStick /></el-icon></el-avatar>
            <div class="a-body">
              <div v-if="m.pending" class="thinking">
                <span class="dot" /><span class="dot" /><span class="dot" />
                <span class="thinking-text">正在检索知识图谱与文献库…</span>
              </div>

              <template v-else-if="m.result">
                <!-- 检索过程 -->
                <div class="steps">
                  <div class="steps-head" @click="m.openSteps = !m.openSteps">
                    <el-icon><component :is="m.openSteps ? 'ArrowDown' : 'ArrowRight'" /></el-icon>
                    <span class="steps-title">检索过程</span>
                    <el-tag size="small" type="info" effect="plain" class="steps-tag">{{ m.result.intent.label }}</el-tag>
                    <span class="steps-sum">
                      共 {{ m.result.steps.reduce((a: number, s: any) => a + s.ms, 0) }} ms · 意图识别 → 三路检索 → RRF
                      融合 → 重排序 → 生成
                    </span>
                  </div>
                  <div v-show="m.openSteps" class="steps-body">
                    <div v-for="(s, i) in m.result.steps" :key="i" class="step">
                      <div class="step-no">{{ i + 1 }}</div>
                      <div class="step-main">
                        <div class="step-name">
                          {{ s.name }}
                          <span class="step-ms">{{ s.ms }} ms</span>
                        </div>
                        <div class="step-detail">{{ s.detail }}</div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 答案 -->
                <div class="answer">
                  <p v-for="(p, i) in m.result.intent.paragraphs" :key="i" class="ans-p">
                    {{ p }}
                    <sup v-if="i < m.result.citations.length" class="cite" @click="openDoc(m.result.citations[i])">
                      [{{ i + 1 }}]
                    </sup>
                  </p>
                </div>

                <!-- 相关疾病 -->
                <div class="ans-tags">
                  <span class="at-label">相关疾病</span>
                  <el-tag v-for="d in m.result.related" :key="d" size="small" effect="light" class="at-tag">{{ d }}</el-tag>
                </div>

                <!-- 图谱路径 -->
                <div class="ans-path">
                  <span class="at-label">知识图谱路径</span>
                  <div class="path-list">
                    <div v-for="(p, i) in m.result.path" :key="i" class="path-row">
                      <span class="pr-node">{{ p.head }}</span>
                      <span class="pr-rel">{{ p.relation }}</span>
                      <span class="pr-node">{{ p.tail }}</span>
                    </div>
                  </div>
                </div>

                <!-- 引用 -->
                <div class="ans-cites">
                  <span class="at-label">参考文献</span>
                  <div class="cite-list">
                    <div v-for="c in m.result.citations" :key="c.id" class="cite-row" @click="openDoc(c)">
                      <span class="cr-no">[{{ c.citeNo }}]</span>
                      <span class="cr-title">{{ c.title }}</span>
                      <span class="cr-meta">{{ c.journal }} · {{ String(c.publishDate).slice(0, 4) }}</span>
                    </div>
                  </div>
                </div>

                <!-- 操作 -->
                <div class="ans-actions">
                  <el-button link size="small" @click="copyAnswer(m)"><el-icon><CopyDocument /></el-icon>复制回答</el-button>
                  <el-button link size="small" @click="regenerate(m)"><el-icon><RefreshRight /></el-icon>重新生成</el-button>
                  <el-button link size="small" :type="m.feedback === 'up' ? 'success' : ''" @click="feedback(m, 'up')">
                    <el-icon><Select /></el-icon>有帮助
                  </el-button>
                  <el-button link size="small" :type="m.feedback === 'down' ? 'danger' : ''" @click="feedback(m, 'down')">
                    <el-icon><CloseBold /></el-icon>无帮助
                  </el-button>
                  <el-button link size="small" type="primary" @click="viewEvidence(m.result)">
                    <el-icon><View /></el-icon>查看引用来源
                  </el-button>
                  <span class="ai-note">内容为知识梳理，不构成诊疗建议</span>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="qa-input">
        <el-input
          v-model="input"
          type="textarea"
          :rows="2"
          resize="none"
          placeholder="请输入慢性病相关问题，例如：2型糖尿病与高血压有哪些关联？"
          @keydown.enter.exact.prevent="send()"
        />
        <div class="input-bar">
          <span class="input-tip">Enter 发送 · Shift + Enter 换行 · 当前为模拟问答，答案由预设知识模板生成</span>
          <div class="input-btns">
            <el-button size="small" @click="input = ''">清空</el-button>
            <el-button type="primary" size="small" :loading="sending" @click="send()">
              <el-icon><Promotion /></el-icon>发送
            </el-button>
          </div>
        </div>
      </div>
    </section>

    <!-- 右：证据面板 -->
    <aside class="qa-evidence">
      <div class="ev-head">
        <span class="ev-title">证据溯源</span>
        <span v-if="currentAnswer" class="ev-sub">{{ currentAnswer.citations.length }} 篇文献 · {{ currentAnswer.path.length }} 条图谱路径</span>
      </div>
      <el-tabs v-model="evidenceTab" class="ev-tabs">
        <el-tab-pane label="文本证据" name="text">
          <div v-if="!allChunks.length" class="ev-empty">发送问题后，这里会展示命中的文本片段与匹配得分</div>
          <div v-else class="ev-list">
            <div v-for="c in allChunks" :key="c.id" class="ev-card">
              <div class="ec-title">{{ c.doc?.title || '文献片段' }}</div>
              <div class="ec-meta">
                <span>{{ c.doc?.journal || c.source }}</span>
                <span>{{ String(c.doc?.publishDate || '').slice(0, 4) }}</span>
              </div>
              <div class="ec-text">{{ c.text }}</div>
              <div class="ec-foot">
                <span class="ec-score">匹配得分 {{ c.score }}</span>
                <el-button link type="primary" size="small" @click="openDoc(c.doc)">查看原文</el-button>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="图谱证据" name="graph">
          <div v-if="!currentAnswer" class="ev-empty">发送问题后，这里会展示图谱中的实体与关系路径</div>
          <template v-else>
            <div class="g-block">
              <div class="g-label">相关实体</div>
              <div class="g-ents">
                <el-tag v-for="d in currentAnswer.related" :key="d" size="small" effect="light" class="g-ent">{{ d }}</el-tag>
              </div>
            </div>
            <div class="g-block">
              <div class="g-label">关系路径</div>
              <div v-for="(p, i) in currentAnswer.path" :key="i" class="g-path">
                <div class="gp-nodes">
                  <span class="gp-node">{{ p.head }}</span>
                  <span class="gp-rel">{{ p.relation }}</span>
                  <span class="gp-node">{{ p.tail }}</span>
                </div>
                <div class="gp-evi">{{ p.rel.source }} · {{ p.rel.section }}</div>
                <div class="gp-snip">{{ p.rel.snippet }}</div>
              </div>
            </div>
            <el-button class="g-btn" type="primary" plain size="small" @click="$router.push('/kg/graph')">
              <el-icon><Share /></el-icon>在知识图谱中查看
            </el-button>
          </template>
        </el-tab-pane>
      </el-tabs>
    </aside>

    <!-- 文献详情 -->
    <el-drawer v-model="docDrawer.visible" title="引用文献" size="560px">
      <div v-if="docDrawer.doc.id">
        <div class="dd-title">{{ docDrawer.doc.title }}</div>
        <div class="dd-meta">
          <el-tag size="small" effect="light">{{ docDrawer.doc.docType }}</el-tag>
          <el-tag size="small" type="info" effect="light">{{ docDrawer.doc.disease }}</el-tag>
          <span class="mz-light">{{ docDrawer.doc.journal }} · {{ String(docDrawer.doc.publishDate).slice(0, 4) }}</span>
        </div>
        <el-descriptions :column="1" border size="small" style="margin-top: 14px">
          <el-descriptions-item label="文献 ID">{{ docDrawer.doc.id }}</el-descriptions-item>
          <el-descriptions-item label="PMID">{{ docDrawer.doc.pmid || '—' }}</el-descriptions-item>
          <el-descriptions-item label="DOI">{{ docDrawer.doc.doi || '暂无' }}</el-descriptions-item>
          <el-descriptions-item label="数据来源">{{ docDrawer.doc.source }}</el-descriptions-item>
          <el-descriptions-item label="文本块">{{ docDrawer.doc.chunkCount }} 块</el-descriptions-item>
        </el-descriptions>
        <div class="dd-sub">摘要</div>
        <div class="dd-abstract">{{ docDrawer.doc.abstract || '暂无摘要' }}</div>
        <div class="dd-note">该文献可在「文献与指南管理」中按文献 ID 检索到，保证问答引用与文献库数据一致。</div>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.qa-page {
  display: flex;
  gap: 12px;
  height: calc(100vh - 60px - 48px);
}
/* 左侧 */
.qa-side {
  width: 248px;
  flex: 0 0 248px;
  background: #fff;
  border: 1px solid var(--mz-border);
  border-radius: var(--mz-radius);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.new-btn {
  margin: 12px;
  height: 36px;
}
.side-label {
  font-size: 11.5px;
  color: var(--mz-text-light);
  padding: 0 14px 8px;
}
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px;
}
.session {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 10px;
  border-radius: 7px;
  cursor: pointer;
  margin-bottom: 2px;
}
.session:hover {
  background: #f5f7fb;
}
.session.active {
  background: var(--mz-primary-soft);
}
.s-body {
  flex: 1;
  min-width: 0;
}
.s-title {
  font-size: 12px;
  color: var(--mz-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.s-meta {
  font-size: 10.5px;
  color: var(--mz-text-light);
  margin-top: 3px;
}
.s-del {
  font-size: 13px;
  color: #c4cad6;
  opacity: 0;
}
.session:hover .s-del {
  opacity: 1;
}
.s-del:hover {
  color: var(--mz-danger);
}
.side-foot {
  padding: 10px 14px;
  border-top: 1px solid var(--mz-border);
}
.sf-line {
  font-size: 10.5px;
  color: #b3bac6;
  line-height: 1.7;
}
/* 中间 */
.qa-main {
  flex: 1;
  min-width: 0;
  background: #fff;
  border: 1px solid var(--mz-border);
  border-radius: var(--mz-radius);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.qa-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  border-bottom: 1px solid var(--mz-border);
}
.head-brand {
  display: flex;
  gap: 10px;
  align-items: center;
}
.brand-badge {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  background: #eff4ff;
  color: #2563eb;
  display: flex;
  align-items: center;
  justify-content: center;
}
.hb-title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--mz-text);
}
.hb-desc {
  font-size: 11px;
  color: var(--mz-text-light);
  margin-top: 2px;
}
.chat-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 20px 22px;
  background: #fcfdff;
}
.welcome {
  max-width: 620px;
  margin: 28px auto 0;
  text-align: center;
}
.w-icon {
  width: 62px;
  height: 62px;
  margin: 0 auto 16px;
  border-radius: 16px;
  background: #f2f6ff;
  border: 1px solid #e2ebfb;
  display: flex;
  align-items: center;
  justify-content: center;
}
.w-title {
  font-size: 17px;
  font-weight: 600;
  color: #173b70;
}
.w-desc {
  font-size: 12.5px;
  color: var(--mz-text-sub);
  line-height: 1.9;
  margin: 8px auto 22px;
  max-width: 480px;
}
.presets {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  text-align: left;
}
.preset {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--mz-border);
  border-radius: 8px;
  padding: 11px 12px;
  cursor: pointer;
  background: #fff;
  transition: all 0.15s;
}
.preset:hover {
  border-color: #c7d8f7;
  box-shadow: 0 3px 10px rgba(37, 99, 235, 0.07);
}
.p-tag {
  font-size: 10px;
  color: #2563eb;
  background: #eff4ff;
  padding: 2px 6px;
  border-radius: 3px;
  white-space: nowrap;
}
.p-q {
  flex: 1;
  font-size: 12px;
  color: var(--mz-text);
  line-height: 1.5;
}
.p-arrow {
  color: #c4cad6;
  font-size: 12px;
}
.msg {
  margin-bottom: 18px;
}
.u-row {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  align-items: flex-start;
}
.u-bubble {
  max-width: 560px;
  background: #2563eb;
  color: #fff;
  font-size: 13px;
  line-height: 1.7;
  padding: 10px 14px;
  border-radius: 10px 2px 10px 10px;
}
.u-avatar {
  background: #173b70;
  font-size: 12px;
  font-weight: 600;
}
.a-row {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.a-avatar {
  background: #eff4ff;
  color: #2563eb;
}
.a-body {
  flex: 1;
  min-width: 0;
  max-width: 100%;
}
.thinking {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 12px 14px;
  background: #fff;
  border: 1px solid var(--mz-border);
  border-radius: 10px;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #93b4f5;
  animation: bounce 1.1s infinite;
}
.dot:nth-child(2) {
  animation-delay: 0.15s;
}
.dot:nth-child(3) {
  animation-delay: 0.3s;
}
@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
  30% { transform: translateY(-4px); opacity: 1; }
}
.thinking-text {
  font-size: 12px;
  color: var(--mz-text-sub);
  margin-left: 6px;
}
.steps {
  background: #fff;
  border: 1px solid var(--mz-border);
  border-radius: 9px;
  margin-bottom: 10px;
  overflow: hidden;
}
.steps-head {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 9px 12px;
  font-size: 12px;
  color: var(--mz-text-sub);
  cursor: pointer;
  user-select: none;
}
.steps-head:hover {
  background: #fafbfd;
}
.steps-title {
  flex: none;
  font-weight: 500;
  color: var(--mz-text);
  white-space: nowrap;
}
.steps-tag {
  flex: none;
}
.steps-sum {
  flex: 1;
  min-width: 0;
  font-size: 11px;
  color: var(--mz-text-light);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.steps-body {
  border-top: 1px solid var(--mz-border);
  padding: 10px 14px 12px;
  background: #fbfcff;
}
.step {
  display: flex;
  gap: 10px;
  padding: 6px 0;
}
.step-no {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #eff4ff;
  color: #2563eb;
  font-size: 10.5px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 18px;
  margin-top: 1px;
}
.step-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--mz-text);
  display: flex;
  gap: 8px;
  align-items: center;
}
.step-ms {
  font-weight: 400;
  font-size: 10.5px;
  color: var(--mz-text-light);
}
.step-detail {
  font-size: 11.5px;
  color: var(--mz-text-sub);
  line-height: 1.7;
  margin-top: 2px;
}
.answer {
  background: #fff;
  border: 1px solid var(--mz-border);
  border-radius: 10px;
  padding: 14px 16px;
}
.ans-p {
  font-size: 13px;
  line-height: 2;
  color: #374151;
  margin: 0 0 10px;
}
.ans-p:last-child {
  margin-bottom: 0;
}
.cite {
  color: #2563eb;
  cursor: pointer;
  font-size: 10px;
  margin-left: 2px;
}
.cite:hover {
  text-decoration: underline;
}
.ans-tags,
.ans-path,
.ans-cites {
  display: flex;
  gap: 10px;
  margin-top: 12px;
  align-items: flex-start;
}
.at-label {
  font-size: 11.5px;
  color: var(--mz-text-light);
  white-space: nowrap;
  padding-top: 3px;
  width: 72px;
  flex: 0 0 72px;
}
.at-tag {
  margin: 0 4px 4px 0;
}
.path-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}
.path-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  background: #f8fafe;
  border: 1px solid #eef2f9;
  border-radius: 6px;
  padding: 5px 10px;
  width: fit-content;
}
.pr-node {
  color: #173b70;
  font-weight: 600;
}
.pr-rel {
  color: #2563eb;
  background: #eff4ff;
  padding: 1px 7px;
  border-radius: 3px;
  font-size: 10.5px;
}
.cite-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.cite-row {
  display: flex;
  gap: 6px;
  font-size: 11.5px;
  color: var(--mz-text-sub);
  cursor: pointer;
  padding: 3px 0;
  align-items: baseline;
}
.cite-row:hover .cr-title {
  color: var(--mz-primary);
  text-decoration: underline;
}
.cr-no {
  color: #2563eb;
  font-family: Consolas, monospace;
}
.cr-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--mz-text);
}
.cr-meta {
  color: var(--mz-text-light);
  white-space: nowrap;
  font-size: 10.5px;
}
.ans-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px dashed #eef1f6;
}
.ai-note {
  margin-left: auto;
  font-size: 10.5px;
  color: var(--mz-text-light);
}
/* 输入区 */
.qa-input {
  border-top: 1px solid var(--mz-border);
  padding: 12px 16px 10px;
  background: #fff;
}
.qa-input :deep(.el-textarea__inner) {
  font-size: 13px;
  line-height: 1.7;
  border-radius: 8px;
  box-shadow: none;
  border: 1px solid var(--mz-border);
  padding: 10px 12px;
}
.input-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}
.input-tip {
  font-size: 10.5px;
  color: var(--mz-text-light);
}
.input-btns {
  display: flex;
  gap: 8px;
}
/* 右 */
.qa-evidence {
  width: 316px;
  flex: 0 0 316px;
  background: #fff;
  border: 1px solid var(--mz-border);
  border-radius: var(--mz-radius);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.ev-head {
  padding: 13px 16px 6px;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}
.ev-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--mz-text);
}
.ev-sub {
  font-size: 10.5px;
  color: var(--mz-text-light);
}
.ev-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0 14px 12px;
}
.ev-tabs :deep(.el-tabs__header) {
  margin-bottom: 8px;
}
.ev-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow-y: auto;
}
.ev-empty {
  padding: 50px 12px;
  text-align: center;
  font-size: 11.5px;
  color: var(--mz-text-light);
  line-height: 1.8;
}
.ev-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ev-card {
  border: 1px solid var(--mz-border);
  border-radius: 8px;
  padding: 10px 12px;
  background: #fcfdff;
}
.ec-title {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--mz-text);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.ec-meta {
  display: flex;
  gap: 8px;
  font-size: 10.5px;
  color: var(--mz-text-light);
  margin: 5px 0 7px;
}
.ec-text {
  font-size: 11px;
  line-height: 1.75;
  color: #6b7280;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.ec-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed #f0f2f6;
}
.ec-score {
  font-size: 10.5px;
  color: #16a34a;
}
.g-block {
  margin-bottom: 14px;
}
.g-label {
  font-size: 11.5px;
  color: var(--mz-text-light);
  margin-bottom: 6px;
}
.g-ents {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.g-ent {
  margin: 0;
}
.g-path {
  border: 1px solid var(--mz-border);
  border-radius: 8px;
  padding: 9px 11px;
  margin-bottom: 8px;
  background: #fcfdff;
}
.gp-nodes {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  flex-wrap: wrap;
}
.gp-node {
  font-weight: 600;
  color: #173b70;
}
.gp-rel {
  color: #2563eb;
  background: #eff4ff;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 10.5px;
}
.gp-evi {
  font-size: 10.5px;
  color: var(--mz-text-light);
  margin-top: 6px;
}
.gp-snip {
  font-size: 11px;
  color: #6b7280;
  line-height: 1.7;
  margin-top: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.g-btn {
  width: 100%;
}
.dd-title {
  font-size: 15px;
  font-weight: 600;
  line-height: 1.6;
}
.dd-meta {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-top: 10px;
  flex-wrap: wrap;
}
.dd-sub {
  font-size: 12.5px;
  font-weight: 600;
  margin: 16px 0 8px;
  padding-left: 8px;
  border-left: 3px solid var(--mz-primary);
}
.dd-abstract {
  font-size: 12.5px;
  line-height: 1.9;
  color: #4b5563;
  background: #fafbfd;
  border: 1px solid #eef1f6;
  border-radius: 8px;
  padding: 12px 14px;
}
.dd-note {
  margin-top: 14px;
  font-size: 11px;
  color: var(--mz-text-light);
  line-height: 1.7;
}
</style>
