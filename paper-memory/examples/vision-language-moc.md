# MOC: Vision-Language Research

*Map of Content for tracking paper relationships, lineage, and research gaps in the Vision-Language (VLM) domain.*

## 1. 基础表示与基线 (Foundations & Baselines)
- [[Transformer]]：提供了用于处理图像序列与语言序列的统一 Backbone 架构。
- [[ResNet]]：传统的卷积神经网络图像特征提取基线。

## 2. 核心工作与演进 (Core Literature & Lineage)

### 跨模态对比预训练 (Contrastive Pre-training)
- [[CLIP]]：利用对称双塔对比损失在大规模互联网图文对上进行弱监督对齐，奠定了开放世界零样本迁移的基石。
- [[ALIGN-2021]]：与 CLIP 几乎同时发布，在大规模嘈杂图文对 (1.8B) 上进行多模态对比对齐。

### 跨模态生成与理解 (Generative Multi-modal Models)
- [[BLIP]]：提出清洗互联网嘈杂文本的 Captioner 并在预训练中融入多模态生成损失，提升了图文理解与生成的双重能力。
- [[BLIP-2]]：引入 Q-Former 桥接冻结的图像编码器与冻结的语言大模型 (LLM)，实现了极低训练开销的多模态交互。

### 稠密与定位对齐 (Dense & Localization Alignment)
- [[GLIP]]：将目标检测重构为短语定位任务，把文本 Token 与视觉目标检测框进行对比对齐，实现零样本目标检测。
- [[DenseCLIP]]：将 CLIP 的全局图像级表征改进为区域与像素级表征，用于提升密集预测任务（分割、检测）的泛化能力。

---

## 3. 关键研究挑战 (Key Domain Questions)
- **空间与几何方位敏感度**：全局对比学习模型极易丢失图像中物体的空间方位、距离和相对几何位置关系。
- **计数与属性绑定**：VLM 模型常出现“属性混淆”或“计数失效”问题（如分不清“红色的衣服和蓝色的裤子”与“蓝色的衣服和红色的裤子”）。
- **细粒度语义区分**：如何不需要高成本标注即可让基础模型区分类目中极度相似的物体类别（如不同种类的鸟类或树叶）。

---

## 4. 当前研究空白与机会 (Research Gaps & Opportunities)
- **视觉特征的非对称蒸馏**：如何将自监督模型（如 [[DINOv2]]）中保留的强几何与深度特征，无损地蒸馏或注入到具有开放语义理解能力的 [[CLIP]] 空间中？
- **多模态长文本对齐**：目前大多数 VLM 模型只能对齐短文本段落，难以在极长篇的文档、视频序列与复杂的三维场景中实现高精度的语义关联。
