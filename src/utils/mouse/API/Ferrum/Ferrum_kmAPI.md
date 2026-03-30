# Ferrum KM API 整理版

- 來源：`https://ferrumllc.github.io/software_api/km_api.html`
- 參考：`https://ferrumllc.github.io/print.html`
- 更新日期：2026-03-26

這份文件把 Ferrum 的文字型 KM API 重新整理成三大區：

- 鍵盤
- 滑鼠
- 特殊功能

## 共通說明

- 命令格式為 `km.xxx(...)`
- line terminator 可用 `\r` / `\n`，官方建議 `\n` 或 `\r\n`
- Ferrum App 的 Software API 會回顯命令並附上 `>>> `
- `Hardware Override` 允許實體輸入搶回控制權
- 按鍵名稱可用字串，也可直接用 key code

---

## 鍵盤

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `km.down(key)` | 按下指定按鍵。 | `km.down(4)`<br>`km.down('A')` |
| `km.up(key)` | 放開指定按鍵。 | `km.up(4)`<br>`km.up('A')` |
| `km.press(key)` | 按一下指定按鍵，等同一次完整的按下與放開。 | `km.press(29)` |
| `km.multidown(key1, key2, ...)` | 同一 frame 送出多個按鍵按下。 | `km.multidown(224, 226, 76)` |
| `km.multiup(key1, key2, ...)` | 同一 frame 送出多個按鍵放開。 | `km.multiup(224, 226, 76)` |
| `km.multipress(key1, key2, ...)` | 同一 frame 送出多個按鍵點擊。 | `km.multipress(224, 226, 76)` |
| `km.mask(key[, state])` | 設定或讀取鍵盤輸入攔截。`1` 啟用、`0` 關閉、`2` 特殊模式。 | `km.mask(26, 1)`<br>`km.mask(26, 0)` |
| `km.isdown(key)` | 讀取指定按鍵是否按下。 | `if km.isdown(44):`<br>`    km.press(44)` |
| `km.init()` | 清除鍵盤 lock / mask 狀態。 | `km.init()` |
| `km.keys([state])` | 啟用、關閉或讀取鍵盤 callback。 | `km.keys(1)`<br>`km.keys(0)` |

### 常用 key code

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `4` | `A` | `km.down(4)` |
| `26` | `W` | `km.down(26)` |
| `29` | `Z` | `km.down(29)` |
| `44` | `Space` | `km.down(44)` |
| `225` | `Left Shift` | `km.down(225)` |
| `228` | `Right Control` | `km.down(228)` |

### 鍵盤狀態說明

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `0` | 未按下 | `km.isdown(44)` |
| `1` | 原始按下 | `km.isdown(44)` |
| `2` | 軟體按下 | `km.isdown(44)` |
| `3` | 兩者皆是 | `km.isdown(44)` |

### 鍵盤 callback 輸出

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `Keys(k1, k2, ...)` | 鍵盤 callback 回傳目前按下中的 key code 清單。 | `km.keys(1)` |

---

## 滑鼠

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `km.left([state])` | 控制或讀取左鍵狀態。`0` 放開、`1` 按下。 | `km.left(1)`<br>`km.left(0)` |
| `km.right([state])` | 控制或讀取右鍵狀態。`0` 放開、`1` 按下。 | `km.right(1)` |
| `km.middle([state])` | 控制或讀取中鍵狀態。 | `km.middle(1)` |
| `km.side1([state])` | 控制或讀取側鍵 1 狀態。 | `km.side1(1)` |
| `km.side2([state])` | 控制或讀取側鍵 2 狀態。 | `km.side2(1)` |
| `km.click(button[, count])` | 依按鍵編號執行點擊。`0` 左鍵、`1` 右鍵、`2` 中鍵、`3` 側鍵 1、`4` 側鍵 2。 | `km.click(0)`<br>`km.click(0, 2)` |
| `km.move(x_amount, y_amount)` | 以相對位移移動滑鼠。 | `km.move(10, -5)` |
| `km.wheel(amount)` | 操作滾輪。正值往上，負值往下。 | `km.wheel(1)`<br>`km.wheel(-1)` |
| `km.lock_mx([state])` | 鎖定或讀取 X 軸輸入攔截。 | `km.lock_mx(1)` |
| `km.lock_my([state])` | 鎖定或讀取 Y 軸輸入攔截。 | `km.lock_my(1)` |
| `km.lock_ml([state])` | 鎖定或讀取左鍵輸入攔截。 | `km.lock_ml(1)` |
| `km.lock_mm([state])` | 鎖定或讀取中鍵輸入攔截。 | `km.lock_mm(1)` |
| `km.lock_mr([state])` | 鎖定或讀取右鍵輸入攔截。 | `km.lock_mr(1)` |
| `km.lock_ms1([state])` | 鎖定或讀取側鍵 1 輸入攔截。 | `km.lock_ms1(1)` |
| `km.lock_ms2([state])` | 鎖定或讀取側鍵 2 輸入攔截。 | `km.lock_ms2(1)` |
| `km.catch_xy(duration[, include_sw_input])` | 回看指定時間內的滑鼠總位移。 | `km.catch_xy(1000)` |

### 滑鼠輸入說明

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `left` | 左鍵 | `km.click(0)` |
| `right` | 右鍵 | `km.click(1)` |
| `middle` | 中鍵 | `km.click(2)` |
| `side1` | 側鍵 1 | `km.click(3)` |
| `side2` | 側鍵 2 | `km.click(4)` |

### 滑鼠 callback

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `km.buttons([state])` | 啟用、關閉或讀取滑鼠按鍵 callback。 | `km.buttons(1)` |
| `km.axes([state])` | 啟用、關閉或讀取滑鼠軸 callback。 | `km.axes(1)` |
| `km.<bitmap_char>\r\n>>> ` | 滑鼠按鍵 callback 輸出格式。 | `km.buttons(1)` |
| `Axes(x, y, scroll)\r\n>>> ` | 滑鼠軸 callback 輸出格式。 | `km.axes(1)` |

---

## 特殊功能

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `km.version()` | 取得版本資訊。 | `km.version()` |
| `km.catch_xy(duration[, include_sw_input])` | 讀取指定時間內的滑鼠位移；若要做滑鼠分析，通常和 `lock_*()` 搭配。 | `km.catch_xy(1000, true)` |

### 方向與時間特性

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `x > 0` | 往右 | `km.move(10, 0)` |
| `x < 0` | 往左 | `km.move(-10, 0)` |
| `y > 0` | 往下 | `km.move(0, 10)` |
| `y < 0` | 往上 | `km.move(0, -10)` |
| `press 75ms ~ 125ms` | `km.press()` 的預設按下時間為隨機區間。 | `km.press(29)` |
| `release 125ms ~ 175ms` | `km.up()` / `km.click()` 的釋放時間會落在隨機區間。 | `km.up(29)` |

### 補充

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `km.version()` | Ferrum App 下會回傳 `kmbox: Ferrum`，用來維持舊 KMBox 相容性。 | `km.version()` |
| `Hardware Override` | 實體輸入可在軟體鎖定時搶回控制權。 | `km.lock_ml(1)` |

