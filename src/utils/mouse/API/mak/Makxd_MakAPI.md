# MAKCU / MAKXD MAK API 整理版

- 來源：`https://makxd.com/en/api`
- 更新日期：2026-03-26

## 共通說明

- MAK API 是 binary surface，不是 `km.xxx(...)` 文字 API
- opcode 會直接對應到 payload
- 這份整理用「opcode / 命令名 / 範例 payload」描述功能

---

## 鍵盤

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `0xC0 keyboard` | 鍵盤 stream。 | `opcode=0xC0, period_frames=1` |
| `0xC1 key_disable` | 鍵盤 disable mask。 | `opcode=0xC1, key_locks_mask[8]=...` |
| `0xC2 key_down` | 按下單鍵。 | `opcode=0xC2, key=4` |
| `0xC3 key_up` | 放開單鍵。 | `opcode=0xC3, key=4` |
| `0xC4 key_press` | 單鍵點擊。 | `opcode=0xC4, key=29` |
| `0xC5 key_init` | 重置鍵盤狀態。 | `opcode=0xC5` |
| `0xC6 key_isdown` | 讀取按鍵狀態。 | `opcode=0xC6, key=44` |
| `0xC7 key_mask` | 鍵盤 mask / lock。 | `opcode=0xC7, key=26, state=1` |
| `0xC8 key_string` | 輸入字串。 | `opcode=0xC8, text="hello"` |
| `0xC9 down_for_key` | 鍵盤定時按下。 | `opcode=0xC9, key=4, delay_ms=120` |
| `0xCA lift_key_after` | 延遲後放開。 | `opcode=0xCA, key=4, delay_ms=120` |
| `0xCB lift_key_once_after` | 延遲後單次放開。 | `opcode=0xCB, key=4, delay_ms=120` |
| `0xCC lift_stop_key` | 停止放開流程。 | `opcode=0xCC, key=4` |
| `0xCD key_layout` | 鍵盤 layout。 | `opcode=0xCD, layout=0` |

### 鍵盤狀態

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `0` | none | `opcode=0xC6, key=44` |
| `1` | raw | `opcode=0xC6, key=44` |
| `2` | soft | `opcode=0xC6, key=44` |
| `3` | both | `opcode=0xC6, key=44` |

### 鍵盤 layout

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `0` | US | `opcode=0xCD, layout=0` |
| `1` | UK | `opcode=0xCD, layout=1` |

---

## 滑鼠

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `0x40 buttons` | 滑鼠按鍵 stream。 | `opcode=0x40, period_frames=1` |
| `0x41 axis` | 滑鼠軸 stream。 | `opcode=0x41, period_frames=1` |
| `0x42 stream` | 按鍵 + 軸合併 stream。 | `opcode=0x42, period_frames=1` |
| `0x43 left` | 左鍵。 | `opcode=0x43, state=1` |
| `0x44 right` | 右鍵。 | `opcode=0x44, state=1` |
| `0x45 middle` | 中鍵。 | `opcode=0x45, state=1` |
| `0x46 side1` | 側鍵 1。 | `opcode=0x46, state=1` |
| `0x47 side2` | 側鍵 2。 | `opcode=0x47, state=1` |
| `0x48 pan` | pan 動作。 | `opcode=0x48` |
| `0x49 tilt` | tilt 動作。 | `opcode=0x49` |
| `0x4A turbo` | 五鍵 turbo / delay table。 | `opcode=0x4A, delay_ms[5]=...` |
| `0x4B remap` | 按鍵重新映射。 | `opcode=0x4B, table=...` |
| `0x4C invert_x` | X 軸反轉。 | `opcode=0x4C, enable=1` |
| `0x4D invert_y` | Y 軸反轉。 | `opcode=0x4D, enable=1` |
| `0x4E swap_xy` | X / Y 對調。 | `opcode=0x4E, enable=1` |
| `0x4F lock` | 鎖定按鍵或軸。 | `opcode=0x4F, state=1, target=1` |
| `0x50 catch` | 捕捉模式。 | `opcode=0x50, mode=0` |
| `0x51 pull_off` | pull-off 策略。 | `opcode=0x51, mode=3, delay_ms=120, vel_pct=60` |
| `0x52 move` | 相對移動。 | `opcode=0x52, x=10, y=-5` |
| `0x53 moveto` | 絕對移動。 | `opcode=0x53, x=960, y=540` |
| `0x54 getpos` | 取得座標。 | `opcode=0x54` |
| `0x55 wheel` | 滾輪。 | `opcode=0x55, delta=1` |
| `0x56 silent` | 靜音 / 隱式滑鼠動作。 | `opcode=0x56` |
| `0x57 click` | 點擊。 | `opcode=0x57, button=0, count=2` |
| `0x58 lift_btn_after` | 延遲放開按鍵。 | `opcode=0x58, button=0, delay_ms=120` |
| `0x59 lift_btn_once_after` | 單次延遲放開按鍵。 | `opcode=0x59, button=0, delay_ms=120` |
| `0x5A down_for_btn` | 按鍵定時按下。 | `opcode=0x5A, button=0, delay_ms=120` |
| `0x5B lock_lift_btn_after` | 延遲鎖定放開按鍵。 | `opcode=0x5B, button=0, delay_ms=120` |
| `0x5C lock_lift_axis_after` | 延遲鎖定放開軸。 | `opcode=0x5C, axis=0, delay_ms=120` |
| `0x5D lift_stop_btn` | 停止按鍵放開流程。 | `opcode=0x5D, button=0` |
| `0x5E lock_lift_stop_btn` | 停止鎖定放開按鍵流程。 | `opcode=0x5E, button=0` |
| `0x5F lock_lift_stop_axis` | 停止鎖定放開軸流程。 | `opcode=0x5F, axis=0` |
| `0x60 deqcfg` | 動態配置快照。 | `opcode=0x60, cfg0=..., cfg1=...` |

### 滑鼠狀態

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `0` | release / disable | `opcode=0x43, state=0` |
| `1` | down / enable | `opcode=0x43, state=1` |
| `2` | silent release | `opcode=0x43, state=2` |

### 滑鼠 button 對照

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `0` | left | `opcode=0x57, button=0` |
| `1` | right | `opcode=0x57, button=1` |
| `2` | middle | `opcode=0x57, button=2` |
| `3` | side1 | `opcode=0x57, button=3` |
| `4` | side2 | `opcode=0x57, button=4` |

---

## 特殊功能

### 一般 / 裝置

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `0x00 echo` | echo 控制。 | `opcode=0x00, enable=1` |
| `0x02 serial` | USB serial。 | `opcode=0x02` |
| `0x25 device_key` | trust key metadata。 | `opcode=0x25` |
| `0x03 screen` | 螢幕尺寸。 | `opcode=0x03, w=1920, h=1080` |
| `0x04 bridge` | bridge mode。 | `opcode=0x04, mode=1` |
| `0x05 device` | 裝置模式。 | `opcode=0x05, mode=2` |
| `0x06 version` | 版本。 | `opcode=0x06` |
| `0x07 help` | opcode 一覽。 | `opcode=0x07` |
| `0x08 reboot` | 重啟。 | `opcode=0x08` |
| `0x18 id` | UUID。 | `opcode=0x18` |
| `0x19 info` | identity snapshot。 | `opcode=0x19` |
| `0x1A led` | 讀 / 設 LED。 | `opcode=0x1A, color=1` |
| `0x1B led_blink` | LED 閃爍。 | `opcode=0x1B` |

### Script / Macro

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `0x1E script` | transient script 狀態快照。 | `opcode=0x1E` |
| `0x20 script_begin` | 開始 transient build。 | `opcode=0x20` |
| `0x22 script_abort` | 取消 transient build。 | `opcode=0x22` |
| `0x24 script_save` | 儲存 transient build。 | `opcode=0x24` |
| `0x09 macro_list` | 讀 macro slot 摘要。 | `opcode=0x09` |
| `0x0A macro_info` | 讀單一 macro slot。 | `opcode=0x0A, slot=1` |
| `0x16 macro_name` | macro 重新命名。 | `opcode=0x16, name="test"` |
| `0x17 macro_delete` | 刪除 macro slot。 | `opcode=0x17, slot=1` |
| `0x26 macro_lock` | macro privacy lock。 | `opcode=0x26, locked=1` |
| `0x21 script_run` | 執行 transient script。 | `opcode=0x21` |
| `0x23 script_stop` | 停止 transient runtime jobs。 | `opcode=0x23` |
| `0x1F script_cancel` | 取消 transient runtime jobs。 | `opcode=0x1F` |
| `0x0C macro_run` | 執行已儲存 macro。 | `opcode=0x0C, slot=1` |
| `0x0D macro_stop` | 停止已儲存 macro。 | `opcode=0x0D` |
| `0x0B macro_select` | 選取 macro slot。 | `opcode=0x0B, slot=1` |
| `0x0E macro_arm` | 設定 armed slot。 | `opcode=0x0E, slot=1` |
| `0x0F macro_binds` | 讀全部 bind。 | `opcode=0x0F` |
| `0x10 macro_bind` | 新增 bind。 | `opcode=0x10` |
| `0x11 macro_unbind` | 刪除 bind。 | `opcode=0x11` |
| `0x12 macro_begin` | 開始錄製 macro。 | `opcode=0x12` |
| `0x13 delay` | scripting context delay。 | `opcode=0x13, ms=100` |
| `0x14 macro_commit` | 提交錄製。 | `opcode=0x14` |
| `0x15 macro_abort` | 中止錄製。 | `opcode=0x15` |

### 與 KM API 對應

| 值 | 描述 | 範例 |
| --- | --- | --- |
| `km.move(...)` | 對應 `0x52 move`。 | `km.move(10, -5)` |
| `km.moveto(...)` | 對應 `0x53 moveto`。 | `km.moveto(960, 540)` |
| `km.click(...)` | 對應 `0x57 click`。 | `km.click(0)` |
| `km.press(...)` | 對應 `0xC4 key_press`。 | `km.press(29)` |
| `km.script_begin()` | 對應 `0x20 script_begin`。 | `km.script_begin()` |
| `km.macro_run(...)` | 對應 `0x0C macro_run`。 | `km.macro_run(1)` |

