# Node.js Installation Verification Script

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Checking Node.js Installation..." -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan

# Check Node.js
try {
    $nodeVersion = node --version
    Write-Host "✓ Node.js is installed!" -ForegroundColor Green
    Write-Host "  Version: $nodeVersion`n" -ForegroundColor White
} catch {
    Write-Host "✗ Node.js is NOT installed" -ForegroundColor Red
    Write-Host "  Please install Node.js from: https://nodejs.org/`n" -ForegroundColor Yellow
    exit 1
}

# Check npm
try {
    $npmVersion = npm --version
    Write-Host "✓ npm is installed!" -ForegroundColor Green
    Write-Host "  Version: $npmVersion`n" -ForegroundColor White
} catch {
    Write-Host "✗ npm is NOT installed" -ForegroundColor Red
    Write-Host "  npm should come with Node.js. Please reinstall Node.js.`n" -ForegroundColor Yellow
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation verified successfully!`n" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Run: npm install" -ForegroundColor White
Write-Host "2. Run: npm run dev`n" -ForegroundColor White


