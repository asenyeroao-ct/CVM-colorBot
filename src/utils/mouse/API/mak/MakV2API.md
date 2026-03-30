# makxd V2 API Reference
## 1. API 分層概覽

makxd V2 提供 **三個層級** 的控制介面：

| 層級 | 介面                              | 特性       | 適用場景             |
| -- | ------------------------------- | -------- | ---------------- |
| L1 | ASCII API (`km.move`, `km.key`) | 人類可讀、易測試 | 調試、腳本、驗證         |
| L2 | Binary API (CMD 0x..)           | 高效、結構化   | SDK、正式整合         |
| L3 | Raw HID (`mo`, streaming)       | 最低層、最強控制 | 高速 / bypass / 研究 |

---

## 2. 通訊協議

### 2.1 Binary Frame Format

**RX（Host → Device）**

```
[0x50] [CMD] [LEN_LO] [LEN_HI] [PAYLOAD...]
```

* 所有多位元數值皆為 **Little-Endian**

**TX（Device → Host）**

* SET：回傳 `[status]`（0=OK, 1=ERR）
* GET：回傳對應 PAYLOAD

---

## 3. 滑鼠（Mouse）

### 3.1 相對移動（Move）

**ASCII**

```
km.move(dx, dy[, segments[, cx1, cy1[, cx2, cy2]]])
```

**Binary**

```
CMD 0x0D
[dx:i16] [dy:i16] [segments:u8] [cx1:i8] [cy1:i8]
```

> 功能：以相對位移方式移動滑鼠，可選擇使用 Bezier 曲線進行擬人化軌跡。

---

### 3.2 絕對移動（MoveTo）

**ASCII**

```
km.moveto(x, y[, segments[, cx1, cy1[, cx2, cy2]]])
```

**Binary**

```
CMD 0x0E
[x:i16] [y:i16] [segments:u8]
[cx1:i16] [cy1:i16] [cx2:i16] [cy2:i16]
```

> 功能：移動到虛擬螢幕的絕對座標，需搭配 `screen(width,height)` 設定。

---

### 3.3 原始 HID 滑鼠幀（Raw Mouse Frame）

**ASCII**

```
km.mo(buttons, x, y, wheel, pan, tilt)
```

**Binary**

```
CMD 0x0B
[buttons:u8] [x:i16] [y:i16]
[wheel:i8] [pan:i8] [tilt:i8]
```

> 功能：直接送出 HID mouse report，屬於最低層控制。

---

### 3.4 滾輪 / 平移 / 傾斜

| 動作 | ASCII             | Binary     |
| -- | ----------------- | ---------- |
| 滾輪 | `km.wheel(delta)` | `CMD 0x18` |
| 平移 | `km.pan(steps)`   | `CMD 0x0F` |
| 傾斜 | `km.tilt(steps)`  | `CMD 0x16` |

---

### 3.5 按鍵控制

| 功能 | ASCII               | Binary CMD  |
| -- | ------------------- | ----------- |
| 左鍵 | `km.left(state)`    | 0x08        |
| 右鍵 | `km.right(state)`   | 0x11        |
| 中鍵 | `km.middle(state)`  | 0x0A        |
| 側鍵 | `km.side1/2(state)` | 0x12 / 0x13 |

---

## 4. 鍵盤（Keyboard）

### 4.1 基本操作

| 動作 | ASCII            | Binary |
| -- | ---------------- | ------ |
| 按下 | `km.down(key)`   | 0xA2   |
| 釋放 | `km.up(key)`     | 0xAA   |
| 點擊 | `km.press(key)`  | 0xA7   |
| 狀態 | `km.isdown(key)` | 0xA4   |

> Key 可使用 **HID Code** 或 **字串名稱**（ASCII API）。

---

### 4.2 文字輸入

```
km.string("Hello World")
```

對應 Binary CMD：`0xA9`

---

## 5. 流式介面（Streaming）

> ⚠ 需 UART ≥ 1Mbps

| 類型 | ASCII           | Binary CMD |
| -- | --------------- | ---------- |
| 按鍵 | `km.buttons()`  | 0x02       |
| 軸  | `km.axis()`     | 0x01       |
| 滑鼠 | `km.mouse()`    | 0x0C       |
| 鍵盤 | `km.keyboard()` | 0xA5       |

---

## 6. 系統與設備控制

| 功能     | ASCII          | Binary |
| ------ | -------------- | ------ |
| 波特率    | `km.baud()`    | 0xB1   |
| Bypass | `km.bypass()`  | 0xB2   |
| LED    | `km.led()`     | 0xB9   |
| 重啟     | `km.reboot()`  | 0xBB   |
| 資訊     | `km.info()`    | 0xB8   |
| 版本     | `km.version()` | 0xBF   |

---

## 8. 語意總結

| 語意動作    | 實際指令                    |
| ------- | ----------------------- |
| 移動滑鼠    | `move` / `CMD 0x0D`     |
| 移動到座標   | `moveto` / `CMD 0x0E`   |
| HID 級控制 | `mo` / `CMD 0x0B`       |
| 回饋監聽    | `axis` / `mouse` stream |