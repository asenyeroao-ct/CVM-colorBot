# Ferrum Net API 整理版

- 來源：`HardwareAPI/kmboxNet+++º-+▌ß.docx`
- 更新日期：2026-03-26

這份文件依 `Kmbox-Net版开发文档` 重寫，重點放在：

- 為什麼要做 Kmbox-Net
- 硬體與接線
- 網路連線與裝置狀態
- `kmNet_*` API

整理方式統一為：

- 值
- 描述
- 範例

## 總覽

Kmbox-Net 是一套走網路的鍵鼠控制方案，文件主張它相較於舊串口方案有幾個優點：

- 透過網路 Socket 通訊，速度較快
- 每台裝置有獨立 IP、埠號與硬體識別
- 不走公開串口協議
- 支援滑鼠、鍵盤、監控、屏蔽與 LCD 顯示控制

## 為什麼要做 Kmbox-Net

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `串口太慢` | 舊方案的串口通訊速度不足，且高頻呼叫容易讓裝置不穩定。 | `use network instead of serial` |
| `協議不公開` | 文件強調不公開協議，降低被特徵化與掃描的風險。 | `private protocol` |
| `不必裝驅動` | 使用網路連線，不需要額外驅動流程。 | `plug and play` |
| `速度更高` | 文件宣稱 100M 網路的通訊速度可顯著高於 115200 波特率串口。 | `near 1000 calls/sec` |
| `自動人工軌跡` | 滑鼠可自動補中間軌跡，降低一步跳到位的異常感。 | `kmNet_mouse_move_auto(...)` |
| `監控與屏蔽` | 可直接讀取與屏蔽物理鍵鼠輸入。 | `monitor / mask` |
| `LCD 支援` | 可直接控制裝置螢幕顯示內容。 | `kmNet_lcd_color(...)` |

## 硬體篇

Kmbox-Net 文件提到裝置包含 4 個 USB 口與 1 個更新按鈕。

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `USB 網口` | 連到電腦後會枚舉成 USB 網卡，用於與盒子通訊、傳輸控制指令。 | `USB NIC` |
| `USB 遊戲機接口` | 連到目標電腦後，會枚舉成標準鍵盤滑鼠，用來控制遊戲電腦。 | `game PC` |
| `USB 鍵鼠接口 x2` | 用來接鍵盤或滑鼠，供盒子控制遊戲電腦。 | `keyboard / mouse input` |
| `USB 高速接口（Type-C）` | 可用於雙機同步等操作，文件註明預設不焊接。 | `Type-C sync` |
| `升級按鈕` | 用於韌體更新。 | `firmware update` |

## 接線與狀態

### 基本接線

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `遊戲機口` | 用藍色 USB 線把盒子的遊戲機口接到電腦，先讓盒子上電。 | `connect game-port USB` |
| `鍵鼠輸入` | 把打遊戲的鍵盤滑鼠接到盒子上。 | `connect keyboard / mouse` |
| `網口 USB` | 先把網口 USB 線接到控制端電腦，才能透過網卡與盒子通訊。 | `connect USB network cable` |

### 狀態列圖示

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `等待連接` | 一般上電枚舉過程中的狀態。 | `waiting` |
| `遊戲機識別到盒子` | 目標電腦正常識別盒子鍵鼠設備。 | `connected` |
| `遊戲機斷開與盒子的連接` | 目標電腦與盒子斷線或休眠。 | `disconnected` |

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `沒接網線時` | 網口圖示顯示打叉。 | `no cable` |
| `等待被連接` | 接入網線後，盒子等待上位機連線。 | `waiting for host` |
| `連接成功` | 上位機透過 `kmNet_init` 連上盒子後，圖示會顯示連線成功。 | `connected by API` |

## 軟體篇

文件描述的使用流程大致如下：

1. 先把網口 USB 線接到控制端電腦
2. 讓系統枚舉出 USB 網卡
3. 把主機 IP 調到與盒子同網段
4. 確認可以 `ping` 到盒子
5. 呼叫 `kmNet_init(...)` 建立控制連線

### 連線

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `kmNet_init(char* ip, char* port, char* uuid)` | 連接盒子。`ip`、`port`、`uuid` 都需以裝置顯示為準。 | `kmNet_init("192.168.2.188", "12345", "uuid")` |

#### 參數說明

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `ip` | 盒子的 IP 位址。 | `192.168.2.188` |
| `port` | 盒子的埠號。 | `12345` |
| `uuid` | 裝置唯一識別碼。 | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |

#### 連線說明

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `每台不同` | 文件強調每台裝置的 IP、埠號、UUID 都不同。 | `read from screen` |
| `以顯示屏為準` | 實際值以盒子顯示屏上顯示的資訊為準。 | `follow device display` |
| `網路圖示` | 狀態列第一個圖示代表網路連線狀態。 | `network icon` |

## 滑鼠

### 基本移動

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `kmNet_mouse_move(short x, short y)` | 立即相對移動滑鼠，沒有中間過渡點。 | `kmNet_mouse_move(100, 100)` |
| `kmNet_mouse_move_auto(int x, int y, int time_ms)` | 自動補中間軌跡，在指定時間內移動到目標座標。 | `kmNet_mouse_move_auto(1920, 1080, 200)` |

#### 移動特性

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `立即移動` | `kmNet_mouse_move` 會一步到位，耗時約 1ms。 | `kmNet_mouse_move(100, 100)` |
| `人工軌跡` | `kmNet_mouse_move_auto` 會補出中間軌跡，較像真人移動。 | `kmNet_mouse_move_auto(1920, 1080, 200)` |
| `time_ms` | 第三個參數是希望在多少毫秒內完成。 | `200` |
| `不宜過短` | 文件提醒 `1ms` 這類時間不合理，容易看起來異常。 | `kmNet_mouse_move_auto(1920, 1080, 1)` |
| `名稱注意` | 文件內示例偶爾寫成 `kmNet_mouse_auto_move`，以函式宣告 `kmNet_mouse_move_auto` 為準。 | `kmNet_mouse_move_auto(...)` |

### 滑鼠按鍵

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `kmNet_mouse_left(int isdown)` | 控制左鍵。`0` 放開、`1` 按下。 | `kmNet_mouse_left(1)` |
| `kmNet_mouse_right(int isdown)` | 控制右鍵。`0` 放開、`1` 按下。 | `kmNet_mouse_right(1)` |
| `kmNet_mouse_middle(int isdown)` | 控制中鍵。`0` 放開、`1` 按下。 | `kmNet_mouse_middle(1)` |
| `kmNet_mouse_wheel(int wheel)` | 控制滾輪。文件定義為正值向下滑、負值向上滑。 | `kmNet_mouse_wheel(1)` |
| `kmNet_mouse_all(int button, int x, int y, int wheel)` | 一次控制滑鼠按鍵、座標與滾輪。 | `kmNet_mouse_all(1, 100, 100, -1)` |

#### 按鍵與滾輪說明

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `isdown = 0` | 放開。 | `kmNet_mouse_left(0)` |
| `isdown = 1` | 按下。 | `kmNet_mouse_left(1)` |
| `wheel > 0` | 下滑。 | `kmNet_mouse_wheel(1)` |
| `wheel < 0` | 上滑。 | `kmNet_mouse_wheel(-1)` |

## 鍵盤

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `kmNet_keydown(int vkey)` | 按下指定鍵。`vkey` 為 HID 鍵碼。 | `kmNet_keydown(4)` |
| `kmNet_keyup(int vkey)` | 放開指定鍵。`vkey` 為 HID 鍵碼。 | `kmNet_keyup(4)` |

#### 鍵盤說明

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `vkey` | 鍵盤按鍵的 HID 鍵碼。 | `4 = A` |
| `keydown` | 對應實體按下。 | `kmNet_keydown(29)` |
| `keyup` | 對應實體放開。 | `kmNet_keyup(29)` |

## 物理鍵鼠監控

這一組函式是直接讀取盒子硬體狀態，不走一般系統 API，文件強調可降低 hook 檢測風險。

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `kmNet_monitor(short enable)` | 開啟或關閉物理鍵鼠狀態監控。文件說明中也出現 `port` 的說法，實作建議以官方 demo 為準。 | `kmNet_monitor(1)` |
| `kmNet_monitor_mouse_left()` | 讀取滑鼠左鍵是否按下。 | `kmNet_monitor_mouse_left()` |
| `kmNet_monitor_mouse_middle()` | 讀取滑鼠中鍵是否按下。 | `kmNet_monitor_mouse_middle()` |
| `kmNet_monitor_mouse_right()` | 讀取滑鼠右鍵是否按下。 | `kmNet_monitor_mouse_right()` |
| `kmNet_monitor_mouse_side1()` | 讀取滑鼠側鍵 1 是否按下。 | `kmNet_monitor_mouse_side1()` |
| `kmNet_monitor_mouse_side2()` | 讀取滑鼠側鍵 2 是否按下。 | `kmNet_monitor_mouse_side2()` |
| `kmNet_monitor_keyboard(int vk_key)` | 讀取指定鍵盤鍵是否按下。 | `kmNet_monitor_keyboard(44)` |

### 監控說明

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `即時狀態` | 這些函式是即時讀取，不會阻塞。 | `poll state` |
| `先啟用監控` | 文件要求先呼叫監控啟用，再查詢鍵鼠狀態。 | `kmNet_monitor(1)` |
| `Port=0` | 文件文字提到 `Port=0` 可關閉監聽。 | `kmNet_monitor(0)` |

## 物理鍵鼠屏蔽

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `kmNet_mask_mouse_left(int enable)` | 屏蔽滑鼠左鍵。 | `kmNet_mask_mouse_left(1)` |
| `kmNet_mask_mouse_right(int enable)` | 屏蔽滑鼠右鍵。 | `kmNet_mask_mouse_right(1)` |
| `kmNet_mask_mouse_middle(int enable)` | 屏蔽滑鼠中鍵。 | `kmNet_mask_mouse_middle(1)` |
| `kmNet_mask_mouse_side1(int enable)` | 屏蔽滑鼠側鍵 1。 | `kmNet_mask_mouse_side1(1)` |
| `kmNet_mask_mouse_side2(int enable)` | 屏蔽滑鼠側鍵 2。 | `kmNet_mask_mouse_side2(1)` |
| `kmNet_mask_mouse_x(int enable)` | 屏蔽滑鼠 X 軸。 | `kmNet_mask_mouse_x(1)` |
| `kmNet_mask_mouse_y(int enable)` | 屏蔽滑鼠 Y 軸。 | `kmNet_mask_mouse_y(1)` |
| `kmNet_mask_mouse_wheel(int enable)` | 屏蔽滑鼠滾輪。 | `kmNet_mask_mouse_wheel(1)` |
| `kmNet_mask_keyboard(short vkey)` | 屏蔽指定鍵盤鍵。 | `kmNet_mask_keyboard(44)` |
| `kmNet_unmask_all()` | 解除所有已設定的物理屏蔽。 | `kmNet_unmask_all()` |

### 屏蔽說明

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `enable = 1` | 開啟屏蔽。 | `kmNet_mask_mouse_left(1)` |
| `enable = 0` | 關閉屏蔽。 | `kmNet_mask_mouse_left(0)` |
| `按鍵或軸` | 屏蔽可針對單鍵、單軸或單滾輪。 | `kmNet_mask_mouse_x(1)` |

## LCD 顯示

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `kmNet_lcd_color(unsigned short rgb565)` | 用指定 RGB565 顏色填滿整個 LCD。 | `kmNet_lcd_color(0x0000)` |
| `kmNet_lcd_picture_bottom(unsigned char* buff_128_80)` | 顯示下半部 128x80 圖片。 | `kmNet_lcd_picture_bottom(buff)` |
| `kmNet_lcd_picture(unsigned char* buff_128_160)` | 顯示整屏 128x160 圖片。 | `kmNet_lcd_picture(buff)` |

### LCD buffer 規格

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `rgb565` | 16-bit RGB565 色碼。 | `0x0000` |
| `128x80x2` | 下半屏圖片資料大小。 | `buff_128_80` |
| `128x160x2` | 整屏圖片資料大小。 | `buff_128_160` |

### LCD 效能備註

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `全屏約 125ms` | 文件給出的測試值。 | `kmNet_lcd_picture(...)` |
| `半屏約 62ms` | 文件給出的測試值。 | `kmNet_lcd_picture_bottom(...)` |

## 升級

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `韌體更新` | 文件提到盒子支援韌體升級。 | `firmware upgrade` |
| `升級工具` | 升級工具原始碼位於 `doc` 資料夾下的升級工具目錄。 | `use upgrade tool` |
| `官方 demo` | 文件建議以官方 demo 的流程為參考。 | `follow demo` |

## 補充

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `主機 IP` | 需與盒子 IP 在同一網段，否則無法通訊。 | `192.168.2.x` |
| `ping` | 連線前可先驗證主機與盒子是否連通。 | `ping device` |
| `每秒呼叫` | 文件宣稱網路版呼叫頻率可接近 1000 次 / 秒。 | `about 1000 calls/sec` |
| `人工軌跡` | 若要避免滑鼠移動過於機械化，優先使用 auto 版本。 | `kmNet_mouse_move_auto(...)` |

