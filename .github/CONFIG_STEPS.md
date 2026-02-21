# 配置步驟 - 快速指南

## ✅ 步驟 1：添加 SSH 公鑰到 Gitee

**您的 SSH 公鑰：**
```
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDKM3imFfgnXYcmRrYO8uCnRZbXQ5kt/GEDkbDYuRTP6Z6UbTXmlPFF5vTBdxQbx+v+UJv97DcxXnVCsxyPn3r/4FRRiafAQC3Oi8culpnD3iJajx2ug3FL8hKH8tpy0RAi8UKBjlleiGeAhK98Uphwj40oJ5vRf2k+/HSvUnk78quEdWsl4BfrM64S8IMk2FWF/yQlAuLjBnXghYPnlMUJaaW8poUELvbY8kezcFsHj8V6fDxT8c6J4utS733LPKl+EckOqcliK9v6qDyob19E/ZFeYfIG60z4gR56fB7UddtyL6t5PqjWXkmd60/0HEa+h7D7tBTNqjoIy/B0hzinQbfIJB2lThsc5kl818k8oXwFC3A2ugCc6E8LosIdFE8a9jGQaYhFx+U1smIdqbuSltyeaWmlK5i14ZemAc7GJ+mo4LC4c+50XPWkCIG3pc+fkbhcl6XaEbsgD/T7L+rrWJF2fNndpLg/zcBBfvfvlnc3HUjJUH1fHjmKcIeHFaT7uPsv+KwQtjacYfcULqo7N/HlBqasAsP38FK1pwHbKreTMsLGOiAgPJV4zJfPaiQPDnxGi2NIbU0CljRSoJU+pd71wrGjoPadQqwpNPn/wmU3aBoHUOGh+ShdSiXVUIEQmaTz1kBVwqAZQKOYQKK6vFRntRi1pvBmrf/tYUPIzQ== your_email@example.com
```

**操作步驟：**
1. 訪問：https://gitee.com/profile/sshkeys
2. 點擊「添加公鑰」
3. **標題**：輸入 `GitHub Actions Sync`
4. **公鑰**：貼上上面的完整公鑰（從 `ssh-rsa` 開始到郵箱結束）
5. 點擊「確定」

---

## ✅ 步驟 2：生成 Gitee 個人訪問令牌

1. 訪問：https://gitee.com/profile/personal_access_tokens
2. 點擊「生成新令牌」
3. 填寫：
   - **令牌描述**：`GitHub Actions Sync`
   - **權限範圍**：勾選 `projects`（倉庫權限）
4. 點擊「提交」
5. **重要**：立即複製生成的 Token（只顯示一次！）

---

## ✅ 步驟 3：獲取 SSH 私鑰（用於 GitHub Secrets）

### 方法 1：使用 PowerShell 命令

運行以下命令獲取私鑰：

```powershell
Get-Content ~/.ssh/id_rsa
```

或者使用完整路徑：
```powershell
Get-Content C:\Users\Administrator\.ssh\id_rsa
```

### 方法 2：使用記事本打開

1. 打開文件資源管理器
2. 前往：`C:\Users\Administrator\.ssh\`
3. 右鍵點擊 `id_rsa` 文件
4. 選擇「開啟方式」→「記事本」
5. 全選並複製所有內容（Ctrl+A, Ctrl+C）

### ⚠️ 重要：SSH 私鑰格式要求

SSH 私鑰必須包含**完整的內容**，格式如下：

```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
NhAAAAAwEAAQAAAYEAyDN4phX4J12HJka2DvLgp0WW10OZLfxhA5Gw2LkUz+melG015pTx
... (多行內容，每行約 70 個字符) ...
-----END OPENSSH PRIVATE KEY-----
```

**複製時注意事項：**
- ✅ 必須包含 `-----BEGIN OPENSSH PRIVATE KEY-----` 開頭行
- ✅ 必須包含 `-----END OPENSSH PRIVATE KEY-----` 結尾行
- ✅ 必須包含中間的所有行（通常有 20-30 行）
- ✅ 每行之間不能有多餘的空行
- ❌ 不要只複製部分內容
- ❌ 不要添加或刪除任何字符
- ❌ 不要修改換行符號

### 驗證私鑰格式

複製後，確認私鑰：
1. 以 `-----BEGIN OPENSSH PRIVATE KEY-----` 開頭
2. 以 `-----END OPENSSH PRIVATE KEY-----` 結尾
3. 中間有多行 Base64 編碼的內容

---

## ✅ 步驟 4：添加 GitHub Secrets

1. 進入您的 GitHub 倉庫：https://github.com/asenyeroao-ct/CVM-colorBot
2. 點擊 **Settings** → **Secrets and variables** → **Actions**
3. 點擊 **New repository secret**，添加以下三個 Secrets：

### Secret 1: `GITEE_USER`
- **Name**: `GITEE_USER`
- **Value**: `asenyeroao-ct`

### Secret 2: `GITEE_PRIVATE_KEY`
- **Name**: `GITEE_PRIVATE_KEY`（必須完全匹配，區分大小寫）
- **Value**: 您的 SSH 私鑰（完整內容，包括 `-----BEGIN OPENSSH PRIVATE KEY-----` 和 `-----END OPENSSH PRIVATE KEY-----`）
- **重要**：
  - 直接貼上從步驟 3 複製的完整私鑰
  - 不要添加額外的空格或換行
  - 確保包含所有行（通常 20-30 行）

### Secret 3: `GITEE_TOKEN`
- **Name**: `GITEE_TOKEN`
- **Value**: 您的 Gitee 個人訪問令牌（步驟 2 中生成的）

---

## ✅ 步驟 5：測試同步

1. 在 GitHub 倉庫中做一個小改動（例如修改 README）
2. 提交並推送：
   ```bash
   git add .
   git commit -m "Test sync to Gitee"
   git push origin main
   ```
3. 前往 GitHub 倉庫的 **Actions** 標籤頁
4. 查看工作流執行狀態
5. 等待完成後，檢查 Gitee 倉庫是否已更新

---

## 📝 配置摘要

- **Gitee 用戶名**: `asenyeroao-ct`
- **倉庫名稱**: `CVM-colorBot`
- **SSH 公鑰位置**: `C:\Users\Administrator\.ssh\id_rsa.pub`
- **SSH 私鑰位置**: `C:\Users\Administrator\.ssh\id_rsa`

---

## 🔍 故障排除

如果同步失敗，請檢查：
1. ✅ SSH 公鑰已添加到 Gitee（https://gitee.com/profile/sshkeys）
2. ✅ Gitee Token 已生成並有 `projects` 權限
3. ✅ GitHub Secrets 已正確設置（三個 Secrets 都存在且名稱正確）
4. ✅ SSH 私鑰格式正確（包含完整的 BEGIN/END 標記）
5. ✅ 工作流文件路徑正確：`.github/workflows/sync-to-gitee.yml`

### 常見錯誤

**錯誤：`Permission denied (publickey)`**
- 原因：SSH 認證失敗
- 解決：檢查 `GITEE_PRIVATE_KEY` Secret 是否正確設置，確認對應的公鑰已添加到 Gitee

**錯誤：`已存在同地址倉庫`**
- 原因：Gitee 上已存在同名倉庫
- 解決：這通常不會阻止同步，工作流程會自動使用現有倉庫

**詳細故障排除指南：** 請參考 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
