# kmA（Kmbox A 簡易版）API Reference

> 本文件整理 **kmbox A（簡易版）** 的 Python / 上位機 API 能力，內容來自官方 Python 文件與《kmboxA 版本用戶手冊》，重點放在 **上位機可調用 API（非脫機腳本 UI）**，方便二次開發與自寫控制程式。

---

## 1. 裝置與通訊模型

- 裝置類型：USB HID（鍵盤 + 滑鼠）
- 無需驅動，系統自帶 HID
- 上位機透過 **USB HID 通道** 直接向盒子下發控制指令
- 支援兩種模式：
  - **上位機模式**（Python / C / C++ 控制）
  - **脫機模式**（板載腳本，非本文重點）

---

## 2. API 能力總覽

| 類別 | 能力 |
|---|---|
| 滑鼠 | 移動、點擊、按下/釋放、滾輪 |
| 鍵盤 | press / down / up |
| 延遲 | 固定 / 隨機延遲（配合腳本或上位機） |
| LCD | 字串顯示、圖片刷新 |
| 裝置 | VID/PID 設定、版本資訊 |

---

## 3. 鍵盤 API

> 鍵值皆為 **HID Key Code（u8）**，完整表請見手冊附錄

### 3.1 press(key)

- 功能：單擊按鍵（down + up）

```python
KM_press(key)
```

---

### 3.2 down(key)

- 功能：按鍵保持按下

```python
KM_down(key)
```

---

### 3.3 up(key)

- 功能：釋放按鍵

```python
KM_up(key)
```

---

## 4. 滑鼠 API

### 4.1 move(x, y)

- 功能：相對移動滑鼠
- 座標：
  - X：右正 / 左負
  - Y：下正 / 上負

| 模式 | 範圍 |
|---|---|
| 上位機模式 | -32767 ~ +32767 |
| 脫機腳本 | -4095 ~ +4095 |

```python
KM_move(x, y)
```

✅ **kmA 有『移動』能力，屬於相對移動（非絕對）**

---

### 4.2 按鍵控制

| 函式 | 說明 | state |
|---|---|---|
| left(state) | 左鍵 | 0=放開, 1=按下 |
| right(state) | 右鍵 | 0 / 1 |
| middle(state) | 中鍵 | 0 / 1 |
| side1(state) | 側鍵1 | 0 / 1 |
| side2(state) | 側鍵2 | 0 / 1 |

```python
KM_left(1)
KM_left(0)
```

---

### 4.3 wheel(delta)

- 功能：滾輪控制
- 範圍：-127 ~ +127
  - 正值：下滾
  - 負值：上滾

```python
KM_wheel(delta)
```

---

## 5. 延遲 API

### 5.1 delay(ms)

```python
KM_delay(ms)
```

---

### 5.2 random_delay(min_ms, max_ms)

```python
KM_delay(min_ms, max_ms)
```

- 若 `max_ms = 0` → 固定延遲

---

## 6. LCD API

### 6.1 LCD 字串顯示

```python
KM_LCDstr(mode, text, x, y)
```

| 參數 | 說明 |
|---|---|
| mode | 0=關閉顯示, 1=顯示 |
| text | ASCII 字串（不支援中文） |
| x,y | 顯示位置 |

---

### 6.2 LCD 圖片刷新

- 使用 BMP 點陣資料
- 需配合取模工具產生陣列

---

## 7. 裝置控制

### 7.1 VID / PID 修改

- 功能：修改 USB 裝置識別
- **永久保存，會重啟裝置**

```python
KM_set_vid_pid(vid, pid)
```

---

### 7.2 裝置資訊

- 韌體版本
- 授權狀態
- 裝置 ID

---

## 8. 能力邊界說明（很重要）

### kmA 有什麼

✅ 相對滑鼠移動
✅ 滑鼠點擊 / 滾輪
✅ 鍵盤 press / down / up
✅ LCD 顯示

### kmA 沒有什麼

❌ 絕對座標移動（無 moveto）
❌ Bezier / 曲線移動
❌ 高速 Streaming
❌ Raw HID 幀控制

> 若你需要 **平滑軌跡 / 高頻 / bypass / DMA 級玩法** → 必須用 **kmbox B / makxd V2**
