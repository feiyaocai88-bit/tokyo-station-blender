东京站模型 V11 — 站台、广场、设备建筑与丸之内线细化
2026-11-03 / Blender 5.2 LTS

打开 Tokyo_Station_Detailed_V11.blend 即可；所需图片和字体已打包。
previews 目录含14张渲染图；详细参考来源和估算说明见 sources_and_licenses/detail_refinement_v11.json。

本次更新
1. 10组站台：薄顶板下真实留空的边缘凹槽、支墩、托臂和电缆线槽。
2. 分组柱型：H型钢、圆柱、组合柱、双柱门架、方柱包覆及石材/不锈钢柱面；303处柱身细化。
3. 5/6番线：绿色圆弧中部顶棚与较低侧翼；南端单独保留两根历史铸铁柱的模型表达。
4. 广场：6888块铺装面、15组树池和石座边、排水槽、检修盖；两个圆形通风塔改为低塔身和宽挑檐。
5. 建筑：参考Google Maps街景的竖向格栅设备围护楼；132处窗户细节、落水管、入口灯具和设备楼维修构件。
6. 既有JR列车：48个模板补充空调格栅、轴箱、空气弹簧、连挂软管等细节，沿用原编组和车身。
7. 新增丸之内线M17东京站：B2岛式站台、B1站厅、三组楼梯/扶梯、升降机、两处闸机、36组半高站台门、圆形花岗岩柱及第三轨。
8. 新增六节2000系列车：红色车身、圆形端窗、白色波纹带、驾驶窗框、车内座椅与吊环、转向架、空调和受流靴。
9. V10中的差异化屋顶、8座屋顶设备房、469块隔音屏和5座轨旁设备建筑均包含在此文件中。

查看方法
- 主场景显示完整站房、地面铁路和两座地下车站。
- 在Outliner展开 V11_Review_Cameras，选择相机后使用 Ctrl+小键盘0 切换；小键盘0进入相机视图。
- 相机01–03：广场、屋顶与通风塔。
- 相机04–09：站台柱子、镂空底部、设备楼、立面、JR车辆与屋顶设备。
- 相机10–12：丸之内线站台、车头与B1站厅。
- 右上角Scene下拉切换到“V11 Marunouchi cutaway”，查看去掉B1、外墙和顶棚的B2剖视（相机13）。
- 切换到“V11 2000 series vehicle study”，单独查看一节驾驶车（相机14）；这是与正线列车共享网格的展示副本。

编辑
- V11_Platform_Undercrofts / V11_Platform_Columns：站台底部和柱子。
- V11_Roof_Details / V11_Plaza / V11_Service_Details / V11_Facade_Details：顶棚、广场和建筑。
- V11_Metro_*：丸之内线轨道、站台、楼梯、站厅、列车和照明，按功能拆分。
- V11_Replaced_hidden：保留本次替换前的网格。不要与新网格同时启用渲染，否则会重叠。
- V10、V9及更早版本的原有集合仍保留。

精度与参考
这是参考照片的可编辑场景，不是实测BIM。站台柱型分组、支墩间距、设备楼体量及位置、站内尺寸和部分构件细节为估算；照片跨越不同年份。
设备围护楼参考Google Maps上Ito Imaji的2018年3月全景；2015年街景仅辅助观察街边关系，不用于2017年后广场铺装。
丸之内线层级和功能关系参照东京Metro的2026年4月站内图。为避开原模型的总武线地下站端部结构，沿旧示意线方向向西侧调整约7.35米；具体标高和尺寸未经测量。
JR换乘通道仅为短支路示意，未重建整个地下步行网络。
参考照片、Google街景和运营方图纸未作为贴图或文件随包分发；新增标识使用仓库内OFL许可的Noto Sans JP字体生成网格。

验证
validation/validate_v11.json：原模型几何保留、有限坐标、10组站台、轨道净空、柱子与设施碰撞、屋顶与接触网、丸之内线车辆包络、楼梯净高、展示底板孔洞及两座地下站之间的碰撞检查。
validation/validate_v10_regression.json：原V10顶棚、隔音屏和设备楼回归检查。
保留性检查覆盖输入V10的29533个对象；替换前几何和储存变换均保留，不代表所有对象继续同时显示。
净空检查用于模型质量核对，不是铁路工程安全认证。

复现
脚本在 scripts/ 下。先将仓库原始发布版运行 mod10_platform_context.py 得到V10，再运行 mod11_refinement.py。
例如：
blender --background V10.blend --python-exit-code 1 --python scripts/mod11_refinement.py -- Tokyo_Station_Detailed_V11.blend build_v11.json baseline_v10.json
blender --background Tokyo_Station_Detailed_V11.blend --python-exit-code 1 --python scripts/validate11_refinement.py -- baseline_v10.json validate_v11.json
blender --background Tokyo_Station_Detailed_V11.blend --python-exit-code 1 --python scripts/render_review_cams_v11.py -- previews 64

原项目：https://github.com/feiyaocai88-bit/tokyo-station-blender
本次代码更新：https://github.com/feiyaocai88-bit/tokyo-station-blender/pull/1
