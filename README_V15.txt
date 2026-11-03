东京站 V15：地下站双侧开放展示
日期：2026-11-03，Blender 5.2.3 LTS

打开 Tokyo_Station_Cutaway_V15.blend；这是包含 V14 全部地面内容的完整模型。
总武／横须贺线和丸之内线地下站在主场景中均已打开侧面；实体网格已分离，
使用实体（Solid）视图即可查看，不依赖透明材质或 V9 的着色器剖切开关。

本次调整
- JR B5 至 B1 的外侧围墙、端墙、轨道旁饰面、B4/B1 站厅围墙打开。
- JR 设备层隔墙及短隧道两侧/端部围合打开，保留设备和通风竖井。
- 丸之内线 B2 轨道侧墙和 B1 站厅侧墙打开，换乘支通道侧墙一起打开。
- M7/M8 地下楼梯井及 B1 连接通道侧墙打开，地面的玻璃入口亭保留。
- 与移除墙体对应的墙面海报、站名板、壁灯和瓷砖缝一起隐藏，避免悬空。
- 保留各层楼板、顶板、站台、轨道、列车、柱子、楼梯/扶梯、栏杆、闸机、
  吊挂标识、设备柜、水箱、风机和管线。地面模型沿用 V14。

查看方式
- 默认打开 Tokyo Station 主场景的地下侧面相机。
- V15_Review_Cameras 中有 5 个相机：JR 双侧、M17 站台/站厅、M8 入口、完整模型侧面。
- 场景 V15 JR open sides 和 V15 Metro open sides 只隔离展示地下构件；
  它们与主场景共用同一套网格，不是另做一个没有同步到主场景的版本。
- 默认关闭灯光/相机辅助线叠加（Overlays > Extras），便于观察室内结构。

原件与恢复
原墙体及被拆分的完整原网格保存在主场景的 V15_Replaced_hidden 集合中。
不要直接只打开整个集合，否则其中的原楼板会与开放版本重叠。
可以使用 scripts/restore15_underground_walls.py 将原对象放回、隐藏开放版本，另存一份：
blender -b Tokyo_Station_Cutaway_V15.blend --python-exit-code 1 -P scripts/restore15_underground_walls.py -- Tokyo_Station_Walls_Restored.blend

复现与检查命令见仓库 README.md。validation 记录本次拆分、网格保留与侧面通透检查。
这是为展示内部结构而做的剖开表达；实车、建筑与位置精度仍沿用 V14 的说明。
