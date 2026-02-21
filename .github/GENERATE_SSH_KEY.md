# 生成 SSH 密鑰對指南

## Windows 系統生成 SSH 密鑰

### 方法 1：使用 Git Bash（推薦）

1. 打開 **Git Bash**（如果已安裝 Git for Windows）

2. 運行以下命令生成密鑰：
   ```bash
   ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
   ```
   - 按 Enter 使用默認路徑：`C:\Users\YourName\.ssh\id_rsa`
   - 設置密碼（可選，直接按 Enter 跳過）
   - 再次確認密碼

3. 密鑰生成後，查看公鑰：
   ```bash
   cat ~/.ssh/id_rsa.pub
   ```
   複製整個輸出（從 `ssh-rsa` 開始到郵箱結束）

4. 查看私鑰：
   ```bash
   cat ~/.ssh/id_rsa
   ```
   複製整個輸出（包括 `-----BEGIN OPENSSH PRIVATE KEY-----` 和 `-----END OPENSSH PRIVATE KEY-----`）

### 方法 2：使用 PowerShell

1. 打開 **PowerShell**

2. 運行以下命令：
   ```powershell
   ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
   ```

3. 按 Enter 使用默認路徑：`C:\Users\YourName\.ssh\id_rsa`

4. 設置密碼（可選）

5. 查看公鑰：
   ```powershell
   Get-Content ~/.ssh/id_rsa.pub
   ```

6. 查看私鑰：
   ```powershell
   Get-Content ~/.ssh/id_rsa
   ```

## 重要提示

- **公鑰** (`id_rsa.pub`)：添加到 Gitee SSH 公鑰頁面
- **私鑰** (`id_rsa`)：添加到 GitHub Secrets（作為 `GITEE_PRIVATE_KEY`）

## 下一步

1. 將**公鑰**添加到 Gitee（當前頁面）
2. 將**私鑰**添加到 GitHub Secrets
