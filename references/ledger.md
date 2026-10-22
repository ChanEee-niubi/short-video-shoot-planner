# 独立素材台账

格式见 `example-plan.json`。Python 3.9+。ID 用非空字符串；数量由条目计算。

## 字段

- `source_rows`：所有包含画面需求或无法明确拆分的源行。每项有 `id`、`script`、`sheet`、`row`、`shot_ids`；无可计数画面时须有 `unresolved` 或 `no_shot_reason`。
- `shots`：每项有 `id`、`source_row`、`description`、`delivery`（`onsite`／`ai`／`external`）、`status`（`ready`／`conditional`）。条件项必须有 `condition`。口播主画面填 `speech_id`，补充特写不填。同一脚本同段口播的多个主画面可以沿用 speech ID；不同脚本不能共用。
- `groups`：按拍摄顺序排列，每项有 `id`、`label`、`shot_ids`，仅放实拍（包括条件实拍）。可加 `note` 用于 Excel。
- `speech_grouping_exception`：仅在现场依赖导致口播无法集中且已向用户说明时填具体原因；一般省略。

`unresolved` 表示该行还有未确定的部分，允许与已明确的 `shot_ids` 并存；`no_shot_reason` 用于确认无独立画面的纯字幕、旁白等。二者不可拿来掩盖遗漏。

## 口径

计划实拍 = ready onsite + conditional onsite。AI 和外部素材另计，条件 AI／外部素材仍标 condition，不得称为已完成。口播段数为不同 speech ID 数量，口播画面数为带 speech ID 的实拍条目数。

示例中 A 为口播1＋面料1＋按压1；B 为口播1＋面料1＋按压1＋条件搬运1＋AI1。结果：可直接拍6，条件实拍1，计划实拍7，AI1，口播2段。第二组始终是四条独立素材。

## 拆分边界

- “女生坐下后自然躺下，固定中景”可连续一条，不按两个动词算两条。
- “坐下中景、腰背贴合特写、再切表情”需要三幅独立画面；同机位长素材截取多个片段也属于复用，需明确允许。
- “正躺、侧躺、趴卧分别展示”拆三条；“多角度”须标假设。
- “对镜讲解拆芯，插入拉链及层材特写”通常一段口播、至少三个画面，依据原文补足拆分。
- A、B都要求按压面料，分别建 ID、分别拍，只共用拍摄阶段。

## 人工复核

程序只能验证输入的台账。源行清单遗漏、自然语言拆错时仍可能通过。必须逐行对照原文件：每行有去向、每个拆分有依据、每个未知有标记。不能把程序 PASS 描述为语义已自动验证。
