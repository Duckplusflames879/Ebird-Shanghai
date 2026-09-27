# 上海本地观鸟辅助系统/Ebird-Shanghai

可以直接双击 `index.html` 打开应用。观鸟点默认使用程序内置的 eBird API Key，进入“观鸟点”页面会先展示本地缓存并尽快打开地图，再在后台按 10 分钟节流检查更新；手动“刷新数据”会强制重新获取并就地更新标记。设置页可输入新的个人 API Key 覆盖默认配置。

如果不希望联网获取，也可以在“设置 → 观鸟点数据”中导入 eBird 最近 7 日 JSON。导入文件与浏览器在线获取使用完全相同的数据格式。

## eBird 观鸟点数据

观鸟点数据统一使用 eBird 上海区域 `CN-31` 的最近 7 日热点观测。页面直接从 eBird API 获取，eBird 官方还提供带地理坐标的 Hotspot 列表和区域代码体系。
查询参数固定为最近 7 日、热点观测、详细结果和简体中文鸟名；进入系统后的数据会先保存在浏览器本地缓存，以便下一次打开时优先显示上次成功数据，再按节流规则检查更新。
导入只更新观鸟点外部数据，不修改个人观鸟记录、图鉴状态或备忘录。

## 更新方式

程序启动后进入“观鸟点”会自动执行 `EBirdData.fetchRecent()`；内置 Key 会在未保存覆盖 Key 时自动使用，更新成功后直接写入浏览器本地缓存。

离线交换方式使用“导出当前 eBird JSON”和“导入 eBird JSON”。导入文件格式固定为 `shanghai-birding-ebird-7d`，版本号为 1。

## 数据说明

`data/birds.js` 使用当前上传的 544 条上海区域鸟种版本。`data/bird_details.js` 按这份 birds.js 逐条生成 544 份离线详细物种卡。区域覆盖数量以 Avibase 的 Shanghai checklist 为主要基准（页面标示 544 species，最近修改于 2026-02-17）；上海市政府公开信息显示截至 2025 年底上海已记录 543 种野生鸟类。由于不同名录采用的分类体系可能存在 1 种左右的差异，后续更新应以选定权威名录的最新版本为准。

数据 schema 仍保持 `id/name/family/genus` 不变。新增条目使用基于中文名称的稳定哈希 ID；原有条目的 ID 未修改，因此旧记录不会因扩充图鉴而失去关联。
Reference:
- Avibase Shanghai checklist: https://avibase.bsc-eoc.org/checklist.jsp?lang=EN&list=howardmoore&region=cnsn
- 上海市人民政府：上海记录野生鸟类达到 543 种（2026-05-26）

## 图鉴详情

每个图鉴条目（已点亮或未点亮）均可打开详情。所有 544 个鸟种的详细资料均保存在本地，详情只显示分类、属、外观与识别、习性、栖息地、食性、迁徙与上海出现；图鉴详情不依赖联网服务。

物种名录基线采用上海区域 544 种清单；Avibase 当前上海清单显示 544 种，按 Howard and Moore 4th edition 分类体系整理。上海市政府公开信息在 2026 年 5 月公布的记录数为 543 种，因此项目保留 544 条区域清单作为图鉴基线，并在数据文件中记录来源与说明。

## 观鸟点实时数据与点位合并

观鸟点默认数据源为 eBird 公共 API 的上海区域 `CN-31`。

查询使用最近 7 日、热点观测、详细结果和简体中文鸟名。所有记录进入前端后都会经过统一地点和鸟种归一化。

所有观鸟点和鸟种在界面中均使用中文；eBird 没有返回中文鸟名的记录不会进入显示数据。

点击观鸟点后，Leaflet 地图下方会显示该地点按鸟种聚合后的逐条最近观测记录。


More reference: 
- eBird Hotspot FAQ：https://support.ebird.org/en/support/solutions/articles/48001009443-ebird-hotspot-faqs
- eBird 数据下载/API：https://support.ebird.org/en/support/solutions/articles/48000838205-download-ebird-data
- eBird 上海区域：https://ebird.org/region/CN-31

观测频次表示来源记录次数，不等同于实际鸟的数量。
