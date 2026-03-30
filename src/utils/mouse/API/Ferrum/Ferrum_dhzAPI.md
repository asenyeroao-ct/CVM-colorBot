# Ferrum DHZ API 整理版

- 來源：`HardwareAPI/docs/DHZBOX_LITE.docx`
- 更新日期：2026-03-26

這份文件依 `DHZBOX_LITE` 使用手冊整理，重點放在：

- 裝置特性與接線
- 網頁端設定
- 以太網通信 API
- 串口通信 API
- 鍵名附錄

## 總覽

DHZBOX_LITE 是基於香橙派 ZERO3 的網路鍵鼠控制器。文件強調它的特性包括：

- 加密通信
- 可自訂端口與加密密鑰
- 通訊穩定且速度快
- 無需適配鼠標
- 支援裝置參數仿真
- 提供 Web UI
- 支援物理鍵鼠監視與屏蔽
- 同時支援串口與以太網通信

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `加密通信` | 每台 DHZBOX 可自訂通信端口與加密密鑰。 | `UDP + key` |
| `千兆網口` | 裝置本體自帶千兆網口，文件主張速度與穩定性更好。 | `network first` |
| `Linux 解析鼠標` | 裝置直接在 Linux 層解析鼠標，不需要額外適配。 | `no mouse tuning` |
| `Web UI` | 可用瀏覽器設定硬體參數。 | `open 192.168.8.88` |
| `監視 / 屏蔽` | 可讀取或屏蔽物理鍵鼠。 | `monitor / mask` |
| `雙通道` | 同時提供以太網與串口兩種呼叫方式。 | `UDP / serial` |

## 硬體篇

### 介面與配件

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `USB 網卡口` | 連到主控電腦後，會出現 USB 網卡，用於與盒子通訊。 | `USB NIC` |
| `USB 遊戲機口` | 連到受控電腦後，會枚舉成標準鍵盤滑鼠。 | `game port` |
| `USB 鍵鼠口` | 用來接鍵盤或滑鼠。 | `keyboard / mouse input` |
| `Type-C 供電 / 數據線` | 連到受控電腦，供電電壓電流建議為 `5V 3A`。 | `Type-C` |
| `USB2.0 輔助供電` | 鼠標功耗過大時才需要。文件提醒不要先接輔助供電。 | `optional power` |
| `升級按鈕` | 用於韌體更新。 | `firmware update` |

### 啟動與狀態

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `45 秒` | 文件說明系統完全正常啟動約需 45 秒。 | `boot wait` |
| `前端 LED 綠色閃爍` | 代表設備通電成功。 | `power ok` |
| `尾部網口 LED 常亮 / 閃爍` | 代表與主控電腦通信成功。 | `link ok` |

## 如何接線

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `step1` | 將 USB 網卡與網線對接。 | `plug USB NIC` |
| `step2` | 將網線接入 DHZBOX 網口，USB 網卡插入主控電腦。 | `connect host` |
| `step3` | 將鼠標等輸入設備插入 DHZBOX 的 USB 口。 | `connect input device` |
| `step4` | 將 Type-C 線插入 DHZBOX，再接到受控機。 | `connect target PC` |
| `step5` | 檢查 LED 與連線狀態。 | `check LEDs` |

### 接線注意

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `5V 3A` | 供電不可超過文件建議值。 | `safe power` |
| `USB2.0 輔助供電` | 若主供電足夠，通常不需要。 | `optional` |
| `重新插拔` | 若狀態異常，可重新插拔遊戲機線重啟。 | `replug cable` |

## 03 網卡驅動

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `USB 網卡驅動` | 如果系統出現磁碟或驅動安裝需求，雙擊 exe 安裝即可。 | `run installer` |
| `無感安裝` | 若裝置管理員已無感嘆號，代表驅動已自動安裝。 | `no manual driver` |

## 04 修改網卡 IP

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `192.168.8.XX` | 文件建議 USB 網卡 IP 設成此網段。 | `192.168.8.10` |
| `子網掩碼` | 需在同一網段內與盒子通訊。 | `255.255.255.0` |
| `ping` | 可先用 `ping` 驗證網卡是否通。 | `ping 192.168.8.88` |
| `重啟 DHZBOX` | 改完 IP 後需重啟盒子。 | `reboot device` |
| `網頁地址` | 修改完成後可用瀏覽器訪問盒子。 | `http://192.168.8.88` |

## 05 網頁端功能

### 基本資訊

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `192.168.8.88` | 盒子網頁後台地址。 | `open browser` |
| `硬體信息` | 顯示每次上電後需要連接的端口與密鑰。 | `port + key` |
| `硬體設置` | 設定模擬的裝置資訊。 | `device spoofing` |
| `授權管理` | 顯示 UUID 與授權狀態。 | `license status` |

### 硬體信息 / 設置

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `鍵鼠包` | 可上傳 `mouse.bin` 之類的鍵鼠包。 | `upload mouse.bin` |
| `自定義` | 可手動填寫要仿真的外設資訊。 | `custom device info` |
| `重置` | 若填錯可重置回預設。 | `reset settings` |
| `USB Device Tree Viewer` | 文件建議用來查看 HID 裝置資訊。 | `inspect HID` |
| `自動獲取` | 可以自動抓取當前輸入設備資訊。 | `auto fill` |

### 更新包與鏡像

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `更新包` | V2.0.1 起可直接上傳 `.so` 更新包。 | `upload .so` |
| `重啟盒子` | 更新完成後點擊重啟生效。 | `reboot after update` |
| `鏡像燒寫` | 如需重裝系統，可燒寫 `.img` 鏡像。 | `flash image` |
| `重新授權` | 燒寫鏡像會清除授權，需重新啟用。 | `re-authorize` |

## 開發者教程

### 以太網通信篇

DHZBOX_LITE 文件說明：任何語言都以 UDP 通信為主，向 `192.168.8.88:端口號` 發送加密後的函式內容即可。

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `UDP` | 通信方式。 | `send UDP packet` |
| `192.168.8.88:port` | 預設控制端點位址以頁面顯示為準。 | `host:port` |
| `encrypt_string(input_string, key)` | 加密函式，僅對英文字母做位移，其他字元保留。 | `encrypt_string("KEY_A", 1)` |

#### 控制類函式

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `move(x, y)` | 鼠標相對移動。單次移動超過 127 會自動拆段，段與段間隔 1ms。 | `move(10, 20)` |
| `left(0 / 1)` | 控制鼠標左鍵，`0` 放開、`1` 按下。 | `left(1)` |
| `right(0 / 1)` | 控制鼠標右鍵。 | `right(1)` |
| `middle(0 / 1)` | 控制鼠標中鍵。 | `middle(1)` |
| `wheel(int)` | 控制滾輪，`>0` 下移，`<0` 上移。 | `wheel(-1)` |
| `side1(0 / 1)` | 控制鼠標側鍵 1。 | `side1(1)` |
| `side2(0 / 1)` | 控制鼠標側鍵 2。 | `side2(1)` |
| `mouse(button, x, y, wheel)` | 一次控制按鍵、座標與滾輪。`button` 依文件定義：`1` 左、`2` 右、`4` 中、`0` 釋放。 | `mouse(1, 10, 20, 1)` |
| `keydown(KEY_A)` | 按下鍵盤鍵。 | `keydown(KEY_A)` |
| `keyup(KEY_A)` | 放開鍵盤鍵。 | `keyup(KEY_A)` |

#### 監視類函式

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `monitor(enable)` | 開啟或關閉 UDP 監視。文件示例會傳端口號，實作建議以官方 demo 為準。 | `monitor(1234)` |
| `0|0|0|0|0|{'KEY_B', 'KEY_A'}` | 監視輸出格式，前 5 個欄位對應左、中、右、側1、側2，最後是鍵盤按下清單。 | `monitor(1234)` |
| `monitor_mouse_left()` | 讀取物理鼠標左鍵狀態。 | `monitor_mouse_left()` |
| `monitor_mouse_middle()` | 讀取物理鼠標中鍵狀態。 | `monitor_mouse_middle()` |
| `monitor_mouse_right()` | 讀取物理鼠標右鍵狀態。 | `monitor_mouse_right()` |
| `monitor_mouse_side1()` | 讀取物理鼠標側鍵 1 狀態。 | `monitor_mouse_side1()` |
| `monitor_mouse_side2()` | 讀取物理鼠標側鍵 2 狀態。 | `monitor_mouse_side2()` |
| `monitor_keyboard(vk_key)` | 讀取指定鍵盤鍵狀態。 | `monitor_keyboard(KEY_A)` |

#### 屏蔽類函式

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `mask_left(1 / 0)` | 屏蔽或解除屏蔽鼠標左鍵。 | `mask_left(1)` |
| `mask_right(1 / 0)` | 屏蔽或解除屏蔽鼠標右鍵。 | `mask_right(1)` |
| `mask_middle(1 / 0)` | 屏蔽或解除屏蔽鼠標中鍵。 | `mask_middle(1)` |
| `mask_side1(1 / 0)` | 屏蔽或解除屏蔽鼠標側鍵 1。 | `mask_side1(1)` |
| `mask_side2(1 / 0)` | 屏蔽或解除屏蔽鼠標側鍵 2。 | `mask_side2(1)` |
| `mask_wheel(1 / 0)` | 屏蔽或解除屏蔽滾輪。 | `mask_wheel(1)` |
| `mask_x(1 / 0)` | 屏蔽或解除屏蔽 X 軸。 | `mask_x(1)` |
| `mask_y(1 / 0)` | 屏蔽或解除屏蔽 Y 軸。 | `mask_y(1)` |
| `mask_all(1 / 0)` | 屏蔽或解除屏蔽全部鼠標輸入。 | `mask_all(1)` |
| `mask_keyboard('KEY_A')` | 屏蔽指定鍵盤鍵。 | `mask_keyboard('KEY_A')` |
| `dismask_keyboard('KEY_A')` | 解除指定鍵盤鍵屏蔽。 | `dismask_keyboard('KEY_A')` |
| `dismask_keyboard_all()` | 解除所有鍵盤屏蔽。 | `dismask_keyboard_all()` |

#### 系統類函式

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `system(reboot)` | 重啟 DHZBOX 系統。 | `system(reboot)` |
| `system(poweroff)` | 關閉 DHZBOX 系統。 | `system(poweroff)` |

### 串口通信篇

文件說明：若使用串口通信，需透過 CH340 USB-TTL 模組連接 GPIO。

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `GPIO 8` | 對應 TX。 | `8 -> RXD` |
| `GPIO 10` | 對應 RX。 | `10 -> TXD` |
| `GPIO 14` | 對應 GND。 | `14 -> GND` |
| `CH340` | 串口轉換模組。 | `USB-TTL` |

#### 串口控制類函式

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `move(x, y)` | 鼠標相對移動，單次超過 127 會拆段。 | `move(10, 20)` |
| `left(0 / 1)` | 鼠標左鍵。 | `left(1)` |
| `right(0 / 1)` | 鼠標右鍵。 | `right(1)` |
| `middle(0 / 1)` | 鼠標中鍵。 | `middle(1)` |
| `wheel(int)` | 滾輪控制，`>0` 下移，`<0` 上移。 | `wheel(-1)` |
| `keydown(KEY_A)` | 鍵盤按下。 | `keydown('KEY_A')` |
| `keyup(KEY_A)` | 鍵盤釋放。 | `keyup('KEY_A')` |

#### 串口監視類函式

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `isdown_left()` | 查詢物理左鍵狀態。 | `isdown_left()` |
| `isdown_middle()` | 查詢物理中鍵狀態。 | `isdown_middle()` |
| `isdown_right()` | 查詢物理右鍵狀態。 | `isdown_right()` |
| `isdown_side1()` | 查詢物理側鍵 1 狀態。 | `isdown_side1()` |
| `isdown_side2()` | 查詢物理側鍵 2 狀態。 | `isdown_side2()` |
| `isdown('KEY_A')` | 查詢指定鍵盤鍵是否按下。 | `isdown('KEY_A')` |

#### 串口屏蔽類函式

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `mask_left(1 / 0)` | 屏蔽或解除屏蔽左鍵。 | `mask_left(1)` |
| `mask_right(1 / 0)` | 屏蔽或解除屏蔽右鍵。 | `mask_right(1)` |
| `mask_middle(1 / 0)` | 屏蔽或解除屏蔽中鍵。 | `mask_middle(1)` |
| `mask_side1(1 / 0)` | 屏蔽或解除屏蔽側鍵 1。 | `mask_side1(1)` |
| `mask_side2(1 / 0)` | 屏蔽或解除屏蔽側鍵 2。 | `mask_side2(1)` |
| `mask_wheel(1 / 0)` | 屏蔽或解除屏蔽滾輪。 | `mask_wheel(1)` |
| `mask_x(1 / 0)` | 屏蔽或解除屏蔽 X 軸。 | `mask_x(1)` |
| `mask_y(1 / 0)` | 屏蔽或解除屏蔽 Y 軸。 | `mask_y(1)` |
| `mask_all(1 / 0)` | 屏蔽或解除屏蔽鼠標全部輸入。 | `mask_all(1)` |
| `mask_keyboard('KEY_A')` | 屏蔽指定鍵盤鍵。 | `mask_keyboard('KEY_A')` |
| `dismask_keyboard('KEY_A')` | 解除指定鍵盤鍵屏蔽。 | `dismask_keyboard('KEY_A')` |
| `dismask_keyboard_all()` | 解除所有鍵盤屏蔽。 | `dismask_keyboard_all()` |

#### 串口系統類函式

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `system(reboot)` | 重啟系統。 | `system(reboot)` |
| `system(poweroff)` | 關閉系統。 | `system(poweroff)` |

## 各語言調用

文件列出支援：

- C++
- Python
- 易語言

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `SDK` | 文件提示 SDK 呼叫示例需到交流群下載查看。 | `download from group` |

## 附錄：鍵名

文件強調鍵盤控制只需要傳遞鍵名，不需要傳遞鍵碼。

### 常用鍵名對照

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `KEY_A` | 鍵盤 A。 | `keydown('KEY_A')` |
| `KEY_B` | 鍵盤 B。 | `keydown('KEY_B')` |
| `KEY_ENTER` | Enter。 | `keydown('KEY_ENTER')` |
| `KEY_ESC` | Esc。 | `keydown('KEY_ESC')` |
| `KEY_SPACE` | Space。 | `keydown('KEY_SPACE')` |
| `KEY_LEFTCTRL` | 左 Ctrl。 | `keydown('KEY_LEFTCTRL')` |
| `KEY_RIGHTCTRL` | 右 Ctrl。 | `keydown('KEY_RIGHTCTRL')` |
| `KEY_F1` | F1。 | `keydown('KEY_F1')` |
| `KEY_F12` | F12。 | `keydown('KEY_F12')` |

### 鍵值範圍

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `0x04` | `KEY_A` | `KEY_A = 0x04` |
| `0x1A` | `KEY_W` | `KEY_W = 0x1A` |
| `0x28` | `KEY_ENTER` | `KEY_ENTER = 0x28` |
| `0x2C` | `KEY_SPACE` | `KEY_SPACE = 0x2C` |
| `0xE1` | `KEY_LEFTSHIFT` | `KEY_LEFTSHIFT = 0xE1` |

## 補充說明

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `防呆` | 文件特別提醒供電與接線順序要正確，否則可能燒壞盒子。 | `5V 3A max` |
| `Web UI` | 網頁後台可設定硬體信息、更新包與授權。 | `192.168.8.88` |
| `更新包` | 以 `.so` 形式上傳並重啟生效。 | `upload and reboot` |
| `鏡像` | `.img` 鏡像燒寫相當於重裝系統，會清除授權。 | `flash img` |

