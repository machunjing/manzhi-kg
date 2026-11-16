<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/common/PageHeader.vue'

const tab = ref('basic')
const saving = ref(false)

const basic = reactive({
  name: '慢知 · 慢性病智能知识服务平台',
  shortName: '慢知',
  org: '内蒙古师范大学 计算机科学技术学院',
  version: 'v1.4.2',
  owner: '马春静',
  contact: 'admin@manzhi.edu.cn',
  desc: '面向 2 型糖尿病、高血压与血脂异常的慢性病知识服务与科研辅助平台'
})

const permissions = ref([
  { role: '管理员', modules: ['用户管理', '知识数据管理', '知识图谱管理', '智能问答', '关联分析', '系统设置'], scope: '全部数据', canDelete: true, canReview: true },
  { role: '医学审核员', modules: ['知识数据管理', '知识图谱管理', '关系审核'], scope: '所负责疾病', canDelete: false, canReview: true },
  { role: '普通用户', modules: ['智能问答', '关联分析'], scope: '仅已审核知识', canDelete: false, canReview: false }
])

const sources = ref([
  { name: 'PubMed E-utilities', url: 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils', enabled: true, type: 'API', status: '演示状态' },
  { name: 'MedlinePlus', url: 'https://medlineplus.gov', enabled: true, type: 'API', status: '演示状态' },
  { name: '本地指南 PDF 目录', url: 'D:/毕业设计/开题答辩/数据包/01_外部公开语料/指南PDF', enabled: true, type: '文件', status: '可用' },
  { name: 'DiaKG', url: 'https://github.com/China-Linguistics/DiaKG', enabled: true, type: '图谱', status: '可用' },
  { name: 'OpenCMKG', url: 'https://github.com/OpenCMKG', enabled: false, type: '图谱', status: '未启用' }
])

const models = [
  { label: '大语言模型', value: '智谱 GLM-4', note: '用于答案生成，未接入真实 API' },
  { label: 'Embedding 模型', value: 'BGE-M3', note: '1024 维稠密向量' },
  { label: 'Reranker 模型', value: 'bge-reranker-large', note: 'Cross-Encoder 精排' },
  { label: '向量数据库', value: 'Milvus', note: '集合：manzhi_chunks' },
  { label: '图数据库', value: 'Neo4j', note: '库：manzhi_kg' },
  { label: '关系数据库', value: 'MySQL 8.0', note: '业务元数据' }
]

const params = reactive({ vectorTopK: 20, rerankTopK: 5, rrfK: 60, chunkSize: 300, chunkOverlap: 50, temperature: 0.2 })

async function saveBasic() {
  saving.value = true
  await new Promise((r) => setTimeout(r, 400))
  saving.value = false
  ElMessage.success('系统基本信息已保存（演示环境，仅前端状态）')
}

async function saveParams() {
  try {
    await ElMessageBox.confirm(
      '当前未接入真实配置接口，保存仅修改前端演示状态，不会变更后端模型或检索服务参数。是否继续？',
      '保存检索参数',
      { type: 'warning', confirmButtonText: '仍然保存' }
    )
    ElMessage.success('参数已保存到前端演示状态')
  } catch {
    /* cancelled */
  }
}

function resetParams() {
  Object.assign(params, { vectorTopK: 20, rerankTopK: 5, rrfK: 60, chunkSize: 300, chunkOverlap: 50, temperature: 0.2 })
  ElMessage.info('已恢复为默认参数')
}
</script>

<template>
  <div>
    <PageHeader title="系统设置" desc="查看平台基础信息、权限配置、数据来源与模型/检索参数。未接入真实配置接口的项仅作用于前端演示状态。" />

    <div class="mz-card">
      <el-tabs v-model="tab" class="s-tabs">
        <!-- 基本信息 -->
        <el-tab-pane label="系统基本信息" name="basic">
          <div class="pane">
            <el-form :model="basic" label-width="96px" class="basic-form">
              <el-row :gutter="28">
                <el-col :span="12"><el-form-item label="系统名称"><el-input v-model="basic.name" /></el-form-item></el-col>
                <el-col :span="12"><el-form-item label="系统简称"><el-input v-model="basic.shortName" /></el-form-item></el-col>
                <el-col :span="12"><el-form-item label="所属单位"><el-input v-model="basic.org" /></el-form-item></el-col>
                <el-col :span="12"><el-form-item label="系统版本"><el-input v-model="basic.version" disabled /></el-form-item></el-col>
                <el-col :span="12"><el-form-item label="负责人"><el-input v-model="basic.owner" /></el-form-item></el-col>
                <el-col :span="12"><el-form-item label="联系邮箱"><el-input v-model="basic.contact" /></el-form-item></el-col>
                <el-col :span="24">
                  <el-form-item label="系统说明">
                    <el-input v-model="basic.desc" type="textarea" :rows="3" />
                  </el-form-item>
                </el-col>
                <el-col :span="24">
                  <el-form-item>
                    <el-button type="primary" :loading="saving" @click="saveBasic">保存设置</el-button>
                  </el-form-item>
                </el-col>
              </el-row>
            </el-form>
            <div class="tip-box">
              本系统为医学知识服务与科研辅助系统，不提供个体化诊断、处方与治疗决策建议。
            </div>
          </div>
        </el-tab-pane>

        <!-- 权限 -->
        <el-tab-pane label="用户权限配置" name="perm">
          <div class="pane">
            <el-table :data="permissions" size="small" style="width: 100%">
              <el-table-column prop="role" label="角色" width="110" />
              <el-table-column label="可访问模块" min-width="300">
                <template #default="{ row }">
                  <el-tag v-for="m in row.modules" :key="m" size="small" effect="plain" class="perm-tag">{{ m }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="scope" label="数据范围" width="140" />
              <el-table-column label="审核权限" width="92" align="center">
                <template #default="{ row }">
                  <el-icon v-if="row.canReview" color="#16A34A"><CircleCheck /></el-icon>
                  <el-icon v-else color="#D1D5DB"><CircleClose /></el-icon>
                </template>
              </el-table-column>
              <el-table-column label="删除权限" width="92" align="center">
                <template #default="{ row }">
                  <el-icon v-if="row.canDelete" color="#16A34A"><CircleCheck /></el-icon>
                  <el-icon v-else color="#D1D5DB"><CircleClose /></el-icon>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="84">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="ElMessage.info(`「${row.role}」权限编辑需接入后端 RBAC 接口（演示环境未实现）`)">编辑</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="tip-box">权限配置为演示数据，真实环境由后端 RBAC 模型（用户 - 角色 - 权限）控制。</div>
          </div>
        </el-tab-pane>

        <!-- 数据来源 -->
        <el-tab-pane label="数据来源配置" name="source">
          <div class="pane">
            <el-table :data="sources" size="small" style="width: 100%">
              <el-table-column prop="name" label="数据来源" width="180" />
              <el-table-column prop="type" label="类型" width="80" />
              <el-table-column prop="url" label="地址 / 路径" min-width="320" show-overflow-tooltip />
              <el-table-column label="启用" width="90" align="center">
                <template #default="{ row }">
                  <el-switch v-model="row.enabled" size="small" @change="ElMessage.success(`已${row.enabled ? '启用' : '停用'} ${row.name}（演示操作）`)" />
                </template>
              </el-table-column>
              <el-table-column label="连接状态" width="110">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.status === '可用' ? 'success' : row.status === '演示状态' ? 'warning' : 'info'" effect="light">
                    {{ row.status }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <!-- 模型 -->
        <el-tab-pane label="模型配置展示" name="model">
          <div class="pane">
            <div class="model-grid">
              <div v-for="m in models" :key="m.label" class="model-card">
                <div class="mc-label">{{ m.label }}</div>
                <div class="mc-value">{{ m.value }}</div>
                <div class="mc-note">{{ m.note }}</div>
              </div>
            </div>
            <el-alert type="warning" :closable="false" show-icon style="margin-top: 18px">
              模型配置为只读展示。当前前端原型未接入 GLM-4 / BGE-M3 / Milvus / Neo4j 真实服务，问答结果为预设知识模板生成的模拟回答。
            </el-alert>
          </div>
        </el-tab-pane>

        <!-- 检索参数 -->
        <el-tab-pane label="检索参数" name="param">
          <div class="pane">
            <div class="param-list">
              <div class="param-row">
                <div class="p-name">向量检索 Top-K</div>
                <div class="p-ctrl">
                  <el-input-number v-model="params.vectorTopK" :min="5" :max="100" :step="5" size="small" />
                  <span class="unit-hint">条</span>
                </div>
                <div class="p-desc">从向量库初步召回的候选文本块数量，越大召回越全但重排开销越高。</div>
              </div>
              <div class="param-row">
                <div class="p-name">Reranker 保留 Top-K</div>
                <div class="p-ctrl">
                  <el-input-number v-model="params.rerankTopK" :min="1" :max="20" size="small" />
                  <span class="unit-hint">条</span>
                </div>
                <div class="p-desc">交叉编码器精排后送入大模型的证据片段数量，直接影响引用条数。</div>
              </div>
              <div class="param-row">
                <div class="p-name">RRF 融合参数 k</div>
                <div class="p-ctrl">
                  <el-input-number v-model="params.rrfK" :min="1" :max="100" :step="10" size="small" />
                  <span class="unit-hint">常数</span>
                </div>
                <div class="p-desc">向量检索与图谱检索结果融合时的平滑常数，通常取 60。</div>
              </div>
              <div class="param-row">
                <div class="p-name">切块长度</div>
                <div class="p-ctrl">
                  <el-input-number v-model="params.chunkSize" :min="100" :max="800" :step="50" size="small" />
                  <span class="unit-hint">字符</span>
                </div>
                <div class="p-desc">与数据包中「向量切块清单」一致，当前语料按 300 字符切块。</div>
              </div>
              <div class="param-row">
                <div class="p-name">切块重叠</div>
                <div class="p-ctrl">
                  <el-input-number v-model="params.chunkOverlap" :min="0" :max="200" :step="10" size="small" />
                  <span class="unit-hint">字符</span>
                </div>
                <div class="p-desc">相邻切块的重叠长度，用于避免句子被截断导致语义缺失。</div>
              </div>
              <div class="param-row">
                <div class="p-name">生成温度</div>
                <div class="p-ctrl">
                  <el-slider v-model="params.temperature" :min="0" :max="1" :step="0.1" style="width: 190px" />
                  <span class="unit-hint">{{ params.temperature.toFixed(1) }}</span>
                </div>
                <div class="p-desc">温度越低回答越保守稳定，医学知识问答建议不超过 0.3。</div>
              </div>
            </div>
            <div class="param-foot">
              <el-button type="primary" @click="saveParams">保存参数</el-button>
              <el-button @click="resetParams">恢复默认</el-button>
            </div>
            <div class="tip-box">参数修改仅作用于前端演示状态，不会变更后端检索服务；真实接入后应通过配置中心下发。</div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<style scoped>
.s-tabs {
  padding: 0 20px 16px;
}
.s-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}
.pane {
  padding-top: 4px;
}
.param-list {
  max-width: 940px;
  border: 1px solid var(--mz-border);
  border-radius: 10px;
  overflow: hidden;
}
.param-row {
  display: grid;
  grid-template-columns: 180px 220px 1fr;
  align-items: center;
  gap: 16px;
  padding: 10px 16px;
  border-bottom: 1px solid #f1f4f8;
}
.param-row:last-child {
  border-bottom: none;
}
.param-row:nth-child(odd) {
  background: #fbfcfe;
}
.p-name {
  font-size: 12.5px;
  color: var(--mz-text);
  font-weight: 500;
}
.p-ctrl {
  display: flex;
  align-items: center;
  gap: 8px;
}
.p-desc {
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--mz-text-light);
}
.param-foot {
  margin-top: 16px;
}
.tip-box {
  margin-top: 18px;
  font-size: 11.5px;
  line-height: 1.8;
  color: var(--mz-text-sub);
  background: #fbfcfe;
  border: 1px dashed var(--mz-border);
  border-radius: 8px;
  padding: 10px 14px;
  max-width: 900px;
}
.perm-tag {
  margin: 0 6px 4px 0;
}
.model-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.model-card {
  border: 1px solid var(--mz-border);
  border-radius: 9px;
  padding: 16px 18px;
  background: #fcfdff;
}
.mc-label {
  font-size: 11.5px;
  color: var(--mz-text-light);
}
.mc-value {
  font-size: 15px;
  font-weight: 600;
  color: #173b70;
  margin: 7px 0 5px;
}
.mc-note {
  font-size: 11px;
  color: var(--mz-text-light);
  line-height: 1.6;
}
.unit-hint {
  margin-left: 10px;
  font-size: 11.5px;
  color: var(--mz-text-light);
}
</style>
