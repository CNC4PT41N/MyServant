# 可编辑活动内容

程序启动时读取同目录的 `activities.json`。退出游戏后编辑或替换它，再启动即可生效，不需要游戏内配置界面。

- `activities.json`：当前内容，已启用空洞骑士主题。
- `activities-hollow-knight.json`：空洞骑士版本备份。
- `activities-default.json`：原生活模拟版本；复制为 activities.json 可换回。
- `character.json`：独立角色形象、名称和图片配置。
- `save.json`：资金、技能、活动进度和成果。

空洞骑士主题是桌宠的轻量改编，探险、挑战和送花自动推进，无战斗输入、失败惩罚、任务领取或每日要求。原技能的编号沿用 office、tech、design，分别显示为骨钉、外壳、法术，不清空旧进度。核心活动编号工作、学习也保留，按钮显示为探险、修行，资金显示为吉欧。

## 可改字段

| 字段 | 用途 |
| --- | --- |
| labels | 修行、探险、货币、委托等界面名称 |
| thresholds | 三个递增成长门槛 |
| experience_rates | 四个阶段每小时学习经验 |
| routes → name | 路线名称 |
| routes → courses / results / abilities | 四个课程、四种成果、三种掌握能力 |
| routes → training | 可选的三个修行项目；选择会保存，开始活动时固定该项目 |
| jobs → name / contents / result | 委托名称、轮换内容、完成成果 |
| jobs → route / requirement | 对应路线编号与经验要求 |
| jobs → income / energy / stress | 每小时收入、活力消耗、压力增加 |
| activity_rules | 各活动默认时长、开始饥饿上限和活力下限 |
| animations | 过程动作编号列表，按时间依次切换 |

骨钉的三个项目为旋风劈砍、冲刺劈砍、强力劈砍；法术为复仇之魂、荒芜俯冲、嚎叫幽灵。修改 `routes.design.training` 可修改法术项目名称。未选择项目的旧计划仍按原课程执行；选择后不改变正在执行的项目，下一次开始修行生效。原有四个课程阶段继续决定经验速度。

例：将护送娇嫩花的收入调整为25，修改 `jobs.tester.income` 为25。列表条目应使用英文双引号，遵循JSON格式。

保留三个路线编号及原有工作编号，以便旧存档正常读取；可以添加新工作编号。修改工作门槛不会使已有存档无法读取，新的选择仍需要满足门槛。不要删除正在使用的工作编号。配置格式错误会保留原文件，提示错误并使用原生活模拟内容。

## 动作与贴边

生活模拟动作有 read、notes、organize、code、sketch、draw、review、type。空洞骑士动作有 nail、shell、soul、battle、flower、explore。图片配置对应 `process_nail` 等状态，边缘版本为 `process_nail_left/right/top/bottom`。本次空洞骑士形象已经接好全部六类主题动作和四侧版本。

动作优先级：拖拽最高；贴边时保留对应主题的边缘姿态；普通位置使用对应过程姿态；屏幕反馈只有匹配当前边缘的专用图才能替换贴边姿态。拖拽使用独立 drag.png，不再复用观察素材。

内容配置在启动时生效，角色图片配置可实时刷新。更改主题时仍保持一台电脑一个角色。
