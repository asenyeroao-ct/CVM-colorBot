# GitHub to Gitee 同步故障排除指南

## 常見錯誤及解決方案

### 錯誤 1: `Permission denied (publickey)`

**錯誤訊息：**
```
ERROR:hubmirror:Mirror failed for CVM-colorBot: Cmd('git') failed due to: exit code(128)
  cmdline: git push -f gitee refs/remotes/origin/*:refs/heads/* --tags --prune
  stderr: 'git@gitee.com: Permission denied (publickey).
fatal: Could not read from remote repository.
```

**原因：**
SSH 認證失敗，通常是因為：
1. GitHub Secrets 中沒有設置 `GITEE_PRIVATE_KEY`
2. SSH 私鑰格式不正確
3. 對應的公鑰沒有添加到 Gitee

**解決步驟：**

#### 步驟 1: 檢查 GitHub Secrets

1. 前往 GitHub 倉庫：https://github.com/asenyeroao-ct/CVM-colorBot
2. 點擊 **Settings** → **Secrets and variables** → **Actions**
3. 確認以下三個 Secrets 都存在：
   - `GITEE_USER` (值：`asenyeroao-ct`)
   - `GITEE_PRIVATE_KEY` (SSH 私鑰)
   - `GITEE_TOKEN` (Gitee 個人訪問令牌)

#### 步驟 2: 驗證 SSH 私鑰格式

SSH 私鑰必須包含完整的內容，格式如下：

```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
... (多行內容) ...
-----END OPENSSH PRIVATE KEY-----
```

**重要提示：**
- 必須包含 `-----BEGIN OPENSSH PRIVATE KEY-----` 開頭
- 必須包含 `-----END OPENSSH PRIVATE KEY-----` 結尾
- 必須包含中間的所有行（不能有換行符號錯誤）
- 複製時要確保沒有多餘的空格或換行

#### 步驟 3: 重新生成 SSH 密鑰對（如果需要）

如果私鑰格式不正確，可以重新生成：

**Windows PowerShell:**
```powershell
# 生成新的 SSH 密鑰對
ssh-keygen -t rsa -b 4096 -C "your_email@example.com" -f $env:USERPROFILE\.ssh\id_rsa_gitee

# 查看公鑰（添加到 Gitee）
Get-Content $env:USERPROFILE\.ssh\id_rsa_gitee.pub

# 查看私鑰（添加到 GitHub Secrets）
Get-Content $env:USERPROFILE\.ssh\id_rsa_gitee
```

#### 步驟 4: 添加公鑰到 Gitee

1. 訪問：https://gitee.com/profile/sshkeys
2. 點擊「添加公鑰」
3. **標題**：`GitHub Actions Sync`
4. **公鑰**：貼上完整的公鑰內容（從 `ssh-rsa` 開始到郵箱結束）
5. 點擊「確定」

#### 步驟 5: 更新 GitHub Secrets

1. 前往 GitHub 倉庫的 Secrets 頁面
2. 點擊 `GITEE_PRIVATE_KEY` 旁邊的「更新」
3. 貼上完整的私鑰內容（包括 BEGIN/END 標記）
4. 點擊「更新 secret」

#### 步驟 6: 測試 SSH 連接（可選）

在本地測試 SSH 連接：

```powershell
# 測試 Gitee SSH 連接
ssh -T git@gitee.com
```

如果成功，會看到類似訊息：
```
Hi asenyeroao-ct! You've successfully authenticated, but Gitee.com does not provide shell access.
```

---

### 錯誤 2: `已存在同地址倉庫（忽略大小寫）`

**錯誤訊息：**
```
ERROR:platforms:Destination repo creating failed: {"error":{"base":["已存在同地址倉庫（忽略大小寫）"]}}
```

**原因：**
Gitee 上已經存在同名倉庫（可能是之前創建的）。

**解決方案：**

這個錯誤通常不會阻止同步，因為工作流程會嘗試強制推送。如果仍然失敗：

1. **選項 1：使用現有倉庫**
   - 確保 Gitee 倉庫存在：https://gitee.com/asenyeroao-ct/CVM-colorBot
   - 工作流程會自動使用現有倉庫進行同步

2. **選項 2：刪除並重新創建**
   - 前往 Gitee 倉庫設置頁面
   - 刪除現有倉庫
   - 讓工作流程自動創建新倉庫

3. **選項 3：手動創建空倉庫**
   - 在 Gitee 上手動創建空倉庫
   - 確保倉庫名稱完全匹配：`CVM-colorBot`
   - 工作流程會自動同步內容

---

### 錯誤 3: `GITEE_TOKEN` 無效或權限不足

**錯誤訊息：**
```
ERROR:platforms:Destination repo creating failed: {"error":{"base":["權限不足"]}}
```

**原因：**
Gitee 個人訪問令牌無效或權限不足。

**解決步驟：**

1. **生成新的 Gitee Token：**
   - 訪問：https://gitee.com/profile/personal_access_tokens
   - 點擊「生成新令牌」
   - **令牌描述**：`GitHub Actions Sync`
   - **權限範圍**：必須勾選 `projects`（倉庫權限）
   - 點擊「提交」
   - **立即複製 Token**（只顯示一次！）

2. **更新 GitHub Secrets：**
   - 前往 GitHub 倉庫的 Secrets 頁面
   - 更新 `GITEE_TOKEN` 的值
   - 確保 Token 有 `projects` 權限

---

## 驗證配置

### 檢查清單

在重新運行工作流程之前，請確認：

- [ ] `GITEE_USER` Secret 已設置（值：`asenyeroao-ct`）
- [ ] `GITEE_PRIVATE_KEY` Secret 已設置（完整的 SSH 私鑰）
- [ ] `GITEE_TOKEN` Secret 已設置（有效的 Gitee 個人訪問令牌）
- [ ] SSH 公鑰已添加到 Gitee（https://gitee.com/profile/sshkeys）
- [ ] Gitee Token 有 `projects` 權限
- [ ] Gitee 倉庫存在或可以自動創建

### 測試工作流程

1. 前往 GitHub 倉庫的 **Actions** 標籤頁
2. 選擇 **Sync to Gitee** 工作流程
3. 點擊「Run workflow」手動觸發
4. 查看執行日誌，確認沒有錯誤

---

## 獲取幫助

如果問題仍然存在：

1. **檢查工作流程日誌：**
   - 前往 GitHub Actions 頁面
   - 點擊失敗的工作流程運行
   - 查看詳細的錯誤訊息

2. **驗證 Secrets 設置：**
   - 確保所有 Secrets 名稱正確（區分大小寫）
   - 確保 Secret 值沒有多餘的空格或換行

3. **重新生成所有憑證：**
   - 生成新的 SSH 密鑰對
   - 生成新的 Gitee Token
   - 更新所有 GitHub Secrets

4. **檢查 Gitee 帳號狀態：**
   - 確認 Gitee 帳號正常
   - 確認有創建倉庫的權限

---

## 相關文檔

- [生成 SSH 密鑰指南](GENERATE_SSH_KEY.md)
- [配置步驟指南](CONFIG_STEPS.md)
- [hub-mirror-action 文檔](https://github.com/Yikun/hub-mirror-action)
