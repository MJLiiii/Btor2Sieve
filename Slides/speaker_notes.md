# Btor2Sieve Mid-Project Presentation — Speaker Notes & Subtitles

Corresponding slides: `Slides/sample.pdf` (6 pages)

---

## Slide 1 — Title (`Extracting Implied Constraints from BTOR2 Models`)

### 怎么讲（中文要点）
- 简短问候，点明项目名称 **Btor2Sieve** 以及核心任务：**从 BTOR2 硬件模型中自动提取并验证隐含的字级（word-level）约束**。

### English Subtitles (英文逐字稿)
> "Hi everyone, I'm Mingjia Li. Today I'll present the mid-project update for **Btor2Sieve**, a tool for automatically extracting and validating implied word-level constraints from BTOR2 hardware models."

### 中文对照字幕
> “大家好，我是李明佳。今天向大家汇报 **Btor2Sieve** 的中期进展——这是一个从 BTOR2 硬件模型中自动提取并验证隐含字级约束的工具。”

---

## Slide 2 — Project Goal

### 怎么讲（中文要点）
- 按页面上的三个主条目依次介绍：**Goal（目标）** $\rightarrow$ **Input（输入）** $\rightarrow$ **Output（三项输出）**。
- 强调两个关键词：**word-level**（直接针对位向量和数组，而不是打散成单比特门级电路）和 **independently SMT-validated**（每条约束都经过独立 SMT 求解器严格证明）。

### English Subtitles (英文逐字稿)
> "Let's start with the project goal.
> Our **goal** is to automatically extract hidden **word-level** constraints $C$ over bit-vectors and arrays that are logically implied by a safety property $P$.
> The **input** to our tool is a word-level BTOR2 hardware model, where each `bad` node defines a safety property $P = \neg\text{bad}$.
> The **output** consists of three parts:
> First, a set of independently SMT-validated constraints where $P \Rightarrow C$ is proven to hold.
> Second, summary reports along with standalone `.smt2` proof obligations that anyone can replay in external solvers.
> And third, **Pono** verification results (`verify.json` and `verify.csv`) that measure the impact of these constraints on model checking."

### 中文对照字幕
> “首先来看项目目标。
> 我们的**目标**是从安全性质 $P$ 中，自动提取出关于位向量（bit-vector）和数组（array）的隐含**字级**约束 $C$。
> 工具的**输入**是字级的 BTOR2 硬件模型以及安全性质 $P = \neg\text{bad}$。
> 工具的**输出**包含三部分：
> 第一，经过独立 SMT 求解器严格证明成立的约束（$P \Rightarrow C$）；
> 第二，汇总报告以及可独立重放的 `.smt2` 验证文件；
> 第三，将这些约束用于 **Pono** 模型检验的验证结果（`verify.json` 和 `verify.csv`）。”

---

## Slide 3 — Benchmarks & Preprocessing

### 怎么讲（中文要点）
- 承接上一页的 Input，先用表格介绍我们选用的 **4 组测试集**（手写回归测试、`HWMCC'25` 位向量与数组赛道、`CAV'18` 多属性硬件设计）。
- 然后指着下方两个框解释：**为什么要加 `CAV'18`？**（因为 HWMCC 都是单属性文件，而 `CAV'18` 一个设计里有最多 57 个属性，专门用来测 `--reuse` 跨属性复用）；**做了什么预处理？**（把 `CAV'18` 的多属性模型也拆成单属性文件，同时保留原始行号和属性 ID，方便直接对比）。

### English Subtitles (英文逐字稿)
> "Before looking at the pipeline, let's look at our benchmark suites and preprocessing.
> We evaluate Btor2Sieve on four benchmark groups:
> First, hand-crafted BTOR2 examples for fast regression tests with known expected results.
> Second and third, the **HWMCC'25** bit-vector and array tracks, which test bounds, equalities, implications, bit-masks, and native SMT `select`/`store` array relations.
> Fourth, we added multi-property hardware designs from **CAV'18**, including PicoRV32 and ZipCPU.
> Why did we add CAV'18 benchmarks? Because HWMCC already splits every design into single-property files with only one `bad` node each. In contrast, CAV'18 models contain up to 57 `bad` properties per design, which lets us test cross-property constraint reuse (`--reuse`).
> For preprocessing, we also split those multi-property CAV'18 models into individual single-property files while preserving their original line and property IDs for direct comparison."

### 中文对照字幕
> “在看具体流程之前，先介绍一下我们的基准测试集和预处理工作。
> 我们将测试集分为四组：
> 第一组是手写的 BTOR2 小例子，用于快速回归测试；
> 第二、三组来自 **HWMCC'25** 的位向量（`bv`）和数组（`arrays`）赛道，分别测试上下界、等式、蕴含、掩码以及原生 SMT 数组读写关系；
> 第四组是 **CAV'18** 的多属性处理器设计（如 PicoRV32 和 ZipCPU）。
> 为什么要加入 CAV'18？因为 HWMCC 已经把所有设计拆成了单属性文件（每个文件只有 1 个 `bad`），而 CAV'18 的单个模型包含最多 57 个属性，正好用来测试跨属性约束复用（`--reuse`）。
> 在预处理阶段，我们也把 CAV'18 的多属性模型拆分成了单属性文件，同时完整保留原行号和属性 ID，以便和原多属性版本做直接对比。”

---

## Slide 4 — Workflow

### 怎么讲（中文要点）
- 顺着顶部的 5 个方框从左到右串讲整个流水线：
  1. **用 Pono 读性质 $P$**（Pono 作为前端解析 BTOR2 并导出公式）；
  2. **提取子项词表**（从 $P$ 的子项里抽出变量、数组、常量和谓词）；
  3. **生成候选约束 $C$**（结合语法模板与求解器搜索，生成 6 类候选约束）；
  4. **独立验证与重放**（用 Z3 反证法证明 $P \Rightarrow C$，并导出 `.smt2` 用 cvc5 交叉验证）；
  5. **写回 Pono 模型检验**（把通过验证的 $C$ 写回为 `constraint`，在 Pono 中对比加约束前后的模型检验表现）。

### English Subtitles (英文逐字稿)
> "Here is the five-stage workflow of Btor2Sieve.
> **Step 1, Read $P$ via Pono:** **Pono** serves as our BTOR2 frontend; it reads the hardware model and prints the SMT-LIB formula for the safety property $P = \neg\text{bad}$.
> **Step 2, Subterm Vocabulary:** Directly from $P$'s subterms, we extract all relevant bit-vector words, arrays, constants, and predicates.
> **Step 3, Propose Candidates:** Using both syntactic template rules and solver-guided search, we generate untrusted candidate formulas $C$ across six families: bounds, equalities, disequalities, implications, bit-masks, and array relations.
> **Step 4, Validate and Replay:** For each candidate $C$, an independent **Z3** solver proves $P \Rightarrow C$, and we replay the exported `.smt2` queries in **cvc5** to cross-check every proof.
> **Step 5, Verify with Pono:** Finally, we write the accepted constraints back into the BTOR2 model as `constraint` lines and run **Pono** to measure model-checking performance."

### 中文对照字幕
> “这一页展示了 Btor2Sieve 的五步工作流：
> **第一步，通过 Pono 读取 $P$：** 我们使用 **Pono** 作为 BTOR2 前端，读取硬件模型并输出安全性质 $P = \neg\text{bad}$ 的公式。
> **第二步，提取子项词表：** 直接从性质 $P$ 的子项（subterms）中提取相关的位向量、数组、常量和条件谓词。
> **第三步，生成候选约束 $C$：** 结合语法模板规则和求解器引导搜索，生成涵盖上下界、等式/不等式、蕴含关系、位掩码和数组的候选公式 $C$。
> **第四步，验证与重放：** 用独立的 **Z3** 求解器证明 $P \Rightarrow C$，并将导出的 `.smt2` 查询文件在 **cvc5** 中重放以完成交叉检验。
> **第五步，使用 Pono 进行模型检验：** 最后把验证通过的约束 $C$ 作为 `constraint` 写回 BTOR2 模型，在 **Pono** 中测试对比模型检验的效果。”

---

## Slide 5 — Experimental Results

### 怎么讲（中文要点）
- 先讲左栏 **Overall Summary**：在全部 **413** 个模型上跑完评测（373 个在 46 秒内完成，40 个大型缓存模型触及 300 秒 CPU 上限，**0 报错**）；在 **543** 个属性上提出了 **122,660** 个候选，成功验证通过 **7,409** 条隐含约束（通过率 **6.0%**），跨属性复用额外通过 **689** 条；导出的 **8,641** 个 `.smt2` 验证文件在 **Z3** 和 **cvc5** 中重放实现 **0 不一致（0 mismatches）**。
- 再讲右栏两张表：按类别看，**Implication（3,321 条）** 和 **Bounds（3,008 条）** 占了绝大多数，其次是 **不等式/等式（1,070 条）** 和 **数组约束（10 条）**；按赛道看，`CAV'18` 的多属性与单属性结果高度一致（通过率 **10.8%**），`HWMCC'25` 数组赛道和位向量赛道分别提取出 **1,833** 条和 **3,860** 条有效约束。

### English Subtitles (英文逐字稿)
> "Next, here are our experimental results across all **413** benchmarks.
> Looking at the overall summary on the left:
> **373** models completed within 46 seconds each, 40 large models reached the 300-second CPU limit, and there were **zero** errors.
> Across **543** analyzed properties, all searches completed with zero `UNKNOWN` results.
> Out of **122,660** proposed candidates, **7,409** constraints were accepted—an overall acceptance rate of **6.0%**, with zero vacuous truths.
> Cross-property reuse accepted **689** constraints across multi-property models.
> And in independent SMT replay, all **8,641** exported `.smt2` obligations were checked in both **Z3** and **cvc5** with **zero mismatches**.
> On the right, looking at the breakdown by family: **implications** (3,321) and **bounds** (3,008) account for most of the accepted constraints, followed by **disequalities and equalities** (1,070) and **array** relations (10).
> By benchmark track, acceptance rates are **10.8%** on CAV'18 multi and single tracks, **8.7%** on HWMCC'25 arrays, and **4.5%** on HWMCC'25 bit-vector models."

### 中文对照字幕
> “接下来展示我们在全部 **413** 个基准模型上的最新实验结果。
> 先看左侧的总体汇总：
> **373** 个模型全部在 46 秒内完成分析，40 个大型模型达到 300 秒 CPU 上限，全程 **0 报错**。
> 在分析的 **543** 个属性上，全部完成完整搜索（0 `UNKNOWN`）。
> 在生成的 **122,660** 个候选中，验证通过了 **7,409** 条隐含约束（总体通过率 **6.0%**，0 空真）。
> 在多属性模型上，跨属性复用成功通过了 **689** 条约束。
> 最关键的是，导出的全部 **8,641** 个 `.smt2` 验证文件在 **Z3** 和 **cvc5** 双求解器中重放检验，结果 **100% 一致（0 mismatches）**。
> 再看右侧的分类统计：按家族划分，**蕴含关系（3,321 条）**和**上下界（3,008 条）**占比最高，其次是**不等式/等式（1,070 条）**和**数组约束（10 条）**；按赛道划分，CAV'18 多属性和单属性通过率均为 **10.8%**，HWMCC'25 数组赛道和位向量赛道分别提取出了 **1,833** 条和 **3,860** 条约束。”

---

## Slide 6 — Mid-Project Status & Next Steps

### 怎么讲（中文要点）
- 左栏快速总结已完成的四项核心工作（Pono 前端 + 子项词表、6 类约束生成、Z3 验证 + cvc5 重放 + `btor2sieve verify`、以及 HWMCC'25 + CAV'18 数据集构建与评测）。
- 右栏重点讲接下来的两步计划：
  1. 为直接从模型结构（状态转移/初始状态）导出的候选约束定义对应的蕴含验证义务（implication obligation）；
  2. 深入分析各约束类别的通过率、提取与验证耗时开销、跨属性复用效果以及在 Pono 中的验证表现。

### English Subtitles (英文逐字稿)
> "Finally, here is our mid-project status and next steps.
> On the left, we have completed the **Pono** BTOR2 frontend and subterm vocabulary extraction, template and solver-guided candidate generation across all six families, independent **Z3** validation with **cvc5** replay and `btor2sieve verify`, as well as the **HWMCC'25** and **CAV'18** benchmark evaluation.
> For our **next steps** on the right:
> First, we will define the corresponding implication obligation for candidates derived directly from the model.
> Second, we will further analyze per-family acceptance rates, extraction and validation times, and cross-property reuse.
> Thank you! I'd be happy to take any questions."

### 中文对照字幕
> “最后总结一下当前的中期进度与下一步计划。
> 左侧是我们已完成的工作：包括基于 **Pono** 的 BTOR2 前端与子项词表提取、覆盖全部 6 类约束的模板与求解器引导生成、独立的 **Z3** 验证器与 **cvc5** 重放及 `btor2sieve verify`，以及 **HWMCC'25** 和 **CAV'18** 基准测试集的转换拆分与评测。
> 右侧是接下来的两项重点工作：
> 第一，为直接从模型结构导出的候选约束定义对应的蕴含验证条件（implication obligation）；
> 第二，深入分析各类别的接受率、提取与验证耗时以及跨属性复用效果。
> 我的汇报到此结束，谢谢大家！欢迎提问。”
