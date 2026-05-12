# How to Install Node.js and npm

## Method 1: Direct Download (Recommended - Easiest)

1. **Visit the Node.js website:**
   - Go to: https://nodejs.org/
   - Click on the **LTS (Long Term Support)** version button (recommended)
   - This will download the installer for Windows

2. **Run the installer:**
   - Double-click the downloaded `.msi` file
   - Follow the installation wizard
   - Accept the license agreement
   - Keep all default settings
   - Click "Install"

3. **Restart your terminal:**
   - Close all PowerShell/Command Prompt windows
   - Open a NEW terminal window

4. **Verify installation:**
   ```powershell
   node --version
   npm --version
   ```
   Both commands should show version numbers.

## Method 2: Using winget (Windows Package Manager)

If you have winget installed, run this command in PowerShell (as Administrator):

```powershell
winget install OpenJS.NodeJS.LTS
```

Then restart your terminal.

## Method 3: Using Chocolatey

If you have Chocolatey installed, run:

```powershell
choco install nodejs-lts
```

Then restart your terminal.

## After Installation

Once Node.js is installed, navigate to the frontend directory and run:

```powershell
cd "C:\Users\varad\Downloads\Telegram Desktop\satellite monitering\flood monitoring\frontend"
npm install
npm run dev
```

## Quick Download Link

**Direct download link for Windows 64-bit LTS:**
https://nodejs.org/dist/v20.11.0/node-v20.11.0-x64.msi

(Version may vary - always check nodejs.org for the latest LTS version)


