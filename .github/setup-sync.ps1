# GitHub to Gitee Sync Setup Script
# This script helps you set up automatic synchronization

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GitHub to Gitee Sync Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$GITEE_USER = "asenyeroao-ct"
$GITEE_REPO = "CVM-colorBot"

Write-Host "Gitee User: $GITEE_USER" -ForegroundColor Green
Write-Host "Repository: $GITEE_REPO" -ForegroundColor Green
Write-Host ""

# Check if SSH key exists
$sshKeyPath = "$env:USERPROFILE\.ssh\id_rsa"
$sshPubKeyPath = "$env:USERPROFILE\.ssh\id_rsa.pub"

if (Test-Path $sshPubKeyPath) {
    Write-Host "[✓] SSH key pair found" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your SSH Public Key (for Gitee):" -ForegroundColor Yellow
    Write-Host "----------------------------------------" -ForegroundColor Gray
    Get-Content $sshPubKeyPath
    Write-Host "----------------------------------------" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Copy the above public key and add it to:" -ForegroundColor Yellow
    Write-Host "https://gitee.com/profile/sshkeys" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Your SSH Private Key (for GitHub Secrets):" -ForegroundColor Yellow
    Write-Host "----------------------------------------" -ForegroundColor Gray
    Write-Host "(This will be shown next)" -ForegroundColor Gray
    Write-Host ""
    
    $showPrivate = Read-Host "Do you want to display the private key? (y/n)"
    if ($showPrivate -eq "y" -or $showPrivate -eq "Y") {
        Write-Host ""
        Get-Content $sshKeyPath
        Write-Host ""
        Write-Host "Copy the above private key and add it to GitHub Secrets as 'GITEE_PRIVATE_KEY'" -ForegroundColor Yellow
    }
} else {
    Write-Host "[!] SSH key pair not found" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Generating new SSH key pair..." -ForegroundColor Yellow
    Write-Host ""
    
    $email = Read-Host "Enter your email address"
    if ([string]::IsNullOrWhiteSpace($email)) {
        $email = "your_email@example.com"
    }
    
    ssh-keygen -t rsa -b 4096 -C $email -f $sshKeyPath -N '""'
    
    if (Test-Path $sshPubKeyPath) {
        Write-Host ""
        Write-Host "[✓] SSH key pair generated successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Your SSH Public Key (for Gitee):" -ForegroundColor Yellow
        Write-Host "----------------------------------------" -ForegroundColor Gray
        Get-Content $sshPubKeyPath
        Write-Host "----------------------------------------" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Copy the above public key and add it to:" -ForegroundColor Yellow
        Write-Host "https://gitee.com/profile/sshkeys" -ForegroundColor Cyan
        Write-Host ""
    } else {
        Write-Host "[✗] Failed to generate SSH key pair" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Add SSH Public Key to Gitee:" -ForegroundColor Yellow
Write-Host "   - Go to: https://gitee.com/profile/sshkeys" -ForegroundColor White
Write-Host "   - Click 'Add Public Key'" -ForegroundColor White
Write-Host "   - Title: GitHub Actions Sync" -ForegroundColor White
Write-Host "   - Paste the public key shown above" -ForegroundColor White
Write-Host ""
Write-Host "2. Generate Gitee Personal Access Token:" -ForegroundColor Yellow
Write-Host "   - Go to: https://gitee.com/profile/personal_access_tokens" -ForegroundColor White
Write-Host "   - Click 'Generate New Token'" -ForegroundColor White
Write-Host "   - Description: GitHub Actions Sync" -ForegroundColor White
Write-Host "   - Select 'projects' permission" -ForegroundColor White
Write-Host "   - Copy the token (only shown once!)" -ForegroundColor White
Write-Host ""
Write-Host "3. Add Secrets to GitHub:" -ForegroundColor Yellow
Write-Host "   - Go to your GitHub repository" -ForegroundColor White
Write-Host "   - Settings → Secrets and variables → Actions" -ForegroundColor White
Write-Host "   - Add these three secrets:" -ForegroundColor White
Write-Host ""
Write-Host "     Secret Name: GITEE_USER" -ForegroundColor Cyan
Write-Host "     Secret Value: $GITEE_USER" -ForegroundColor Gray
Write-Host ""
Write-Host "     Secret Name: GITEE_PRIVATE_KEY" -ForegroundColor Cyan
Write-Host "     Secret Value: (Your SSH private key from ~/.ssh/id_rsa)" -ForegroundColor Gray
Write-Host ""
Write-Host "     Secret Name: GITEE_TOKEN" -ForegroundColor Cyan
Write-Host "     Secret Value: (Your Gitee personal access token)" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Test the sync:" -ForegroundColor Yellow
Write-Host "   - Make a small change in your GitHub repository" -ForegroundColor White
Write-Host "   - Push to main branch" -ForegroundColor White
Write-Host "   - Check GitHub Actions tab for sync status" -ForegroundColor White
Write-Host "   - Verify changes appear in Gitee repository" -ForegroundColor White
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
