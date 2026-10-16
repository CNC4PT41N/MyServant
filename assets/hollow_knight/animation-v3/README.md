# 小骑士动作 v3

来源：`Saved/knight-action-redesign-20261016/01-ground.png` 至 `05-interaction.png`。
原始动作板保留；游戏使用 `frames/` 中的透明帧，由 `build_knight_v3.py` 索引、缩放和对齐。

使用内置 imagegen 编辑五张动作板，转换为透明底，去除背景、文字、网格、动态符号、鼠标图标、阴影、墙面、地面与石台。保留角色、手持道具、翅膀及睡眠吊床。未使用 CLI/API 回退。

每张动作板使用同一提示词：

> Edit this sprite sheet for the desktop pet game. Keep exactly the same 1024x1536 layout, all characters in their original positions, poses, proportions, colors and row/column order. Extract the characters and their handheld props onto true transparent background. Remove all paper background, headings, text, grid lines, movement marks, cursor icons, shadows, walls, floors and stone platforms. Preserve wings and the sleep hammock with its ropes, but no wall/platform. Do not redesign characters or add objects.

输入/生成结果：

| 输入 | 透明动作板 | 生成编号 |
| --- | --- | --- |
| 01-ground | ground.png | exec-7e751b4f-66c4-4cc4-9aef-632748a7bab3 |
| 02-side-edges | sides.png | exec-be3daa1a-7191-4070-a11e-cc49f8ff93fa |
| 03-top | top.png | exec-93887cf4-873b-4943-a2dd-fd382cef9d88 |
| 04-bottom | bottom.png | exec-571401a0-cbe3-4ff6-99d3-549f0b9d812c |
| 05-interaction | interaction.png | exec-1b096074-fe10-4f9d-96b4-1bd2f8cf7c96 |

互动板的透明结果包含拖拽、观察、笔记、进食、翅膀五行；安静陪伴复用普通放松动作。完整飞行姿态自带翅膀，不另外叠加翅膀图层。

`character.json` 已启用此版本，旧配置备份在 `Saved/knight-action-redesign-20261016/character-before-v3.json`。修改前后的角色名称保留。存档、活动配置和面板未修改。

普通动作周期24秒，含20秒保持主要姿态及两段2秒姿态变化；拖拽周期6秒。主要姿态保持期间仍有8秒一轮的呼吸和披风微动，使用32个缓存相位，实际桌面尺寸下约1～2像素变化。面具上部和图像接触边界固定。关闭旧版较强的关节动作、整体摇摆与独立翅膀。`screen_contacts` 按透明图的实际轮廓对齐窗口边缘。拖拽期间不使用边缘姿态。

所有动作帧按站立面具宽度统一比例（约95像素），不再把蹲下、蜷缩和悬垂姿势拉到相同高度。若翅膀或道具超过窗口容纳范围，才整体缩小以避免裁切。

持续微动按实际活动自动选择：骨钉/战斗为持钉手与骨钉的小幅调整，外壳为双臂收拢和呼吸，灵魂为双手托举，进食/送花为持物手，探索/笔记为手腕，拖拽为悬垂肢体，睡眠为更明显的呼吸。所有活动均叠加缓慢披风变化，包括四向贴边；面具上部与接触边界固定。`preview_continuous.py` 使用实际渲染器导出普通、四向贴边、互动六组8秒动图到 `continuous-review/`。

实际渲染验收：`Saved/knight-action-redesign-20261016/validate_runtime.py`，输出在同目录 `integrated-review/`。预览中的细线仅标记窗口边界，游戏内不绘制。
