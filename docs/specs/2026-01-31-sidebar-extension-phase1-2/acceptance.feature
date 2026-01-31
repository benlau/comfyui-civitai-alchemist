# language: zh-TW
功能: Civitai Alchemist Sidebar Extension（第一、二階段）
  作為 ComfyUI 使用者
  我想要在 ComfyUI sidebar 中查詢 Civitai 圖片的生成資訊和所需 model
  以便不離開 ComfyUI 介面就能了解重現圖片需要什麼

  背景:
    假設 ComfyUI 已啟動且 Civitai Alchemist extension 已安裝
    並且 extension 的前端 JS 已建置完成（js/main.js 存在）

  場景: Sidebar Tab 可見
    當 使用者查看 ComfyUI 左側 sidebar
    那麼 應該看到 Civitai Alchemist 的 tab icon
    並且 點擊該 icon 後應展開 sidebar panel

  場景: API Key 未設定時顯示提示
    假設 ComfyUI Settings 中的 civitai-alchemist.api_key 為空
    當 使用者點開 Civitai Alchemist sidebar tab
    那麼 應該看到「Civitai API Key not configured」的提示訊息
    並且 應該看到「Open Settings」按鈕
    並且 Image ID 輸入欄位應為 disabled 狀態
    並且 Go 按鈕應為 disabled 狀態

  場景: 透過 Settings 設定 API Key
    假設 使用者尚未設定 API key
    當 使用者點擊 sidebar 中的「Open Settings」按鈕
    那麼 應該開啟 ComfyUI Settings 面板
    當 使用者在 Settings 中找到「Civitai API Key」欄位並輸入有效的 API key
    並且 關閉 Settings 面板回到 sidebar
    那麼 提示訊息應消失
    並且 Image ID 輸入欄位應變為可用狀態

  場景: 使用 Image ID 查詢生成資訊
    假設 API key 已正確設定
    當 使用者在輸入欄位輸入 "116872916"
    並且 點擊 Go 按鈕
    那麼 應該看到載入中狀態（包含步驟文字如「Fetching metadata...」）
    並且 Go 按鈕應暫時變為 disabled
    當 載入完成後
    那麼 應該看到 Generation Info 區域，包含：
      | 欄位      | 說明            |
      | Prompt    | 正向提示詞      |
      | Sampler   | 取樣器名稱      |
      | Steps     | 取樣步數        |
      | CFG Scale | CFG 引導比例    |
      | Size      | 圖片尺寸        |

  場景: 使用完整 URL 查詢
    假設 API key 已正確設定
    當 使用者在輸入欄位輸入 "https://civitai.com/images/116872916"
    並且 點擊 Go 按鈕
    那麼 系統應正確解析出 image ID
    並且 顯示與直接輸入 ID 相同的生成資訊

  場景: 按 Enter 鍵觸發查詢
    假設 API key 已正確設定
    當 使用者在輸入欄位輸入 "116872916"
    並且 按下 Enter 鍵
    那麼 應該觸發查詢（與點擊 Go 按鈕等效）

  場景: Model 列表展示 — 含已存在和缺少的 model
    假設 API key 已正確設定
    並且 使用者已查詢 image ID "116872916" 並取得結果
    那麼 應該看到 Models 列表區域
    並且 每個 model 卡片應顯示：名稱、類型、檔案大小
    並且 已存在的 model 應顯示綠色 ✅ 標示和本地路徑
    並且 缺少的 model 應顯示紅色 ❌ 標示
    並且 應該看到摘要文字「Missing: X of Y」

  場景: Model 列表不顯示下載按鈕
    假設 使用者已查詢 image ID 並看到 model 列表
    那麼 不應該看到任何「Download」按鈕
    並且 不應該看到「Download All」按鈕
    並且 不應該看到「Generate Workflow」按鈕

  場景: 更換查詢目標
    假設 使用者已查詢 image ID "116872916" 並看到結果
    當 使用者將輸入欄位改為 "118577644"
    並且 點擊 Go 按鈕
    那麼 應該顯示載入中狀態
    並且 載入完成後應顯示新的生成資訊和 model 列表
    並且 先前的查詢結果應被完全取代

  場景: 無效 Image ID 的錯誤處理
    假設 API key 已正確設定
    當 使用者輸入不存在的 image ID "99999999999"
    並且 點擊 Go 按鈕
    那麼 應該顯示「Image not found」錯誤訊息

  場景: 無效輸入格式的錯誤處理
    假設 API key 已正確設定
    當 使用者輸入 "not-a-valid-id"
    並且 點擊 Go 按鈕
    那麼 應該顯示格式錯誤的提示訊息

  場景: Prompt 可摺疊
    假設 使用者已查詢 image ID 並看到生成資訊
    那麼 Prompt 區域應該是可摺疊的
    當 使用者點擊 Prompt 區域的摺疊控制
    那麼 Prompt 文字應該收起/展開

  場景: pyproject.toml 符合 ComfyUI Registry 規格
    那麼 pyproject.toml 應包含 [tool.comfy] 區段
    並且 [project.dependencies] 只包含 "requests>=2.31.0"
    並且 不應包含 [project.optional-dependencies].dev
    並且 應包含 [project.optional-dependencies].cli
    並且 不應包含 [[tool.uv.index]] 區段

  場景: 已知測試圖片的完整流程驗證
    假設 API key 已正確設定
    當 使用者依序查詢以下 image ID：
      | Image ID  | 特徵                   |
      | 116872916 | 基本 txt2img + LoRAs   |
      | 118577644 | Hires fix, 7 LoRAs     |
      | 119258762 | Custom VAE, embeddings |
    那麼 每個查詢都應成功顯示生成資訊和 model 列表
    並且 model 列表應正確反映本地 model 的存在狀態
