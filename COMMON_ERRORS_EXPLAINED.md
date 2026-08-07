# 🆘 Common Errors Explained (In Plain English)

Don't panic! This guide explains common problems and how to fix them.

---

## When Things Go Wrong

If you see an error message, look for the matching error below and follow the fix.

---

## ERROR 1: "command not found: brew"

### What This Means
Your computer doesn't know how to run `brew install` commands.

### Why It Happens
You either:
- Don't have Homebrew installed
- Your Terminal doesn't know where Homebrew is

### How to Fix It

**Option A: Install Homebrew first**
1. Open Terminal
2. Copy this entire line:
   ```
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
3. Paste into Terminal and press Enter
4. Wait for it to finish (might ask for your password)
5. Now try installing Azure CLI again:
   ```
   brew install azure-cli
   ```

**Option B: If that doesn't work**
1. Close Terminal completely
2. Open Terminal again
3. Try the command again

### How to Verify It's Fixed
Type: `brew --version`
You should see a version number.

---

## ERROR 2: "command not found: az"

### What This Means
Your computer doesn't have Azure CLI installed, or it's not accessible.

### Why It Happens
- You didn't install Azure CLI in Step 1
- Installation didn't complete properly
- You need to restart Terminal

### How to Fix It

**First, try this:**
1. Close Terminal completely (important!)
2. Open a new Terminal window
3. Try: `az --version`

**If that doesn't work:**
1. Install Azure CLI:
   ```
   brew install azure-cli
   ```
2. Wait for ✓
3. Close and reopen Terminal
4. Try: `az --version`

**If you still get the error:**
1. Try installing with a different method:
   ```
   brew tap azure/cli
   brew install azure-cli
   ```
2. Wait and then try: `az --version`

### How to Verify It's Fixed
Type: `az --version`
You should see a version number like "azure-cli 2.50.0"

---

## ERROR 3: "command not found: docker"

### What This Means
Your computer doesn't have Docker installed or running.

### Why It Happens
- You didn't install Docker in Step 1
- Docker Desktop is not running
- You need to restart Terminal

### How to Fix It

**First, make sure Docker is running:**
1. Open Applications folder
2. Look for "Docker" app
3. Double-click to start it
4. Wait for the Docker icon to appear in the top menu bar (next to the clock)
5. Close Terminal completely
6. Open a new Terminal
7. Try: `docker --version`

**If that doesn't work:**
1. Go to https://www.docker.com/products/docker-desktop
2. Download Docker Desktop for your Mac
3. Follow the installation instructions
4. Start Docker
5. Restart Terminal
6. Try: `docker --version`

### How to Verify It's Fixed
Type: `docker --version`
You should see something like "Docker version 24.0.0"

---

## ERROR 4: "ANTHROPIC_API_KEY not set" or "ANTHROPIC_API_KEY: command not found"

### What This Means
You haven't told your Terminal about your API key, or you didn't type the command correctly.

### Why It Happens
- You skipped Step 4 (setting your API key)
- You typed the command wrong
- You closed Terminal and opened a new one (you have to set it each time)

### How to Fix It

**Do this in Terminal:**
1. Get your API key (if you don't have it saved):
   - Go to https://console.anthropic.com/account/keys
   - Log in
   - Copy the key (starts with `sk-ant-`)

2. Type this exactly (replace `sk-ant-XXX...` with your real key):
   ```
   export ANTHROPIC_API_KEY="sk-ant-XXX..."
   ```

3. Press Enter

4. If there's no error, you're good!

### Example
If your key is `sk-ant-abc123def`, type:
```
export ANTHROPIC_API_KEY="sk-ant-abc123def"
```
Then press Enter.

### How to Verify It's Fixed
Type: `echo $ANTHROPIC_API_KEY`
You should see your API key printed back.

---

## ERROR 5: "No valid credentials found"

### What This Means
Azure doesn't recognize you. You're not logged in.

### Why It Happens
- You skipped Step 3 (logging into Azure)
- Your Azure login expired
- You haven't authenticated with Azure yet

### How to Fix It

1. In Terminal, type:
   ```
   az login
   ```

2. Press Enter

3. Your web browser will automatically open

4. Log in with your Azure email and password

5. You should see "You have logged in successfully"

6. Close the browser window

7. Go back to Terminal and try your command again

### If Browser Doesn't Open
1. Copy this URL: https://microsoft.com/devicelogin
2. Open it in your web browser manually
3. Enter the code that Terminal shows
4. Log in with your Azure account

### How to Verify It's Fixed
Type: `az account show`
You should see your Azure account information.

---

## ERROR 6: "The deployment script won't start" or "permission denied: ./deploy.sh"

### What This Means
Your computer won't run the deploy script, or the script isn't executable.

### Why It Happens
- You're not in the right folder
- The script doesn't have permission to run
- You typed the command slightly wrong

### How to Fix It

**Step 1: Make sure you're in the right folder**
1. In Terminal, type:
   ```
   pwd
   ```
2. Press Enter
3. You should see: `/Users/adedotunadebiaye/fpa-copilot`

**If you're in the wrong folder:**
1. Type:
   ```
   cd /Users/adedotunadebiaye/fpa-copilot
   ```
2. Press Enter

**Step 2: Make the script executable**
1. Type:
   ```
   chmod +x deploy.sh
   ```
2. Press Enter

**Step 3: Try again**
1. Type:
   ```
   ./deploy.sh
   ```
2. Press Enter

### How to Verify It's Fixed
The deployment script should start and show:
```
=== FP&A Copilot Azure Deployment ===

Step 1: Checking prerequisites...
```

---

## ERROR 7: "resource group already exists"

### What This Means
Azure already has a resource group with this name. This is actually OK - it's not a problem!

### Why It Happens
- You ran the deployment before
- You're deploying again to update your app

### How to Fix It
**You don't need to fix anything!** The script will use the existing resource group.

Just let the script continue. It's completely safe and normal.

### Result
Your app will be updated instead of creating a new one.

---

## ERROR 8: "Frontend/Backend URLs don't work"

### What This Means
You get a blank page or error when you try to visit your URLs.

### Why It Happens
- Azure is still starting your app (takes 2-3 minutes sometimes)
- Your application crashed or has an error
- You typed the URL wrong

### How to Fix It

**First, try waiting:**
1. Wait 2-3 minutes
2. Refresh the browser (press F5 or Cmd+R)
3. Try again

**If that doesn't work, check the backend:**
1. Try just the backend first:
   ```
   https://fpa-copilot-backend.azurecontainerapps.io/status
   ```
2. You should see: `"status": "ok"`

**If backend works but frontend doesn't:**
- Frontend might still be starting
- Wait another minute and try again

**If backend doesn't work:**
- Your application has an error
- Check the logs:
  ```
  az containerapp logs show --name fpa-copilot-backend --resource-group fpa-copilot-rg
  ```
- Look for red error messages in the log

---

## ERROR 9: "503 Service Unavailable"

### What This Means
The service exists but isn't responding right now.

### Why It Happens
- Azure is restarting your app
- Your app crashed or has an error
- Azure is updating something

### How to Fix It

1. Wait 1-2 minutes
2. Refresh the page (press F5)
3. Try again

**If it keeps happening:**
1. Wait 5 minutes
2. Try again
3. If still broken, check logs:
   ```
   az containerapp logs show --name fpa-copilot-backend --resource-group fpa-copilot-rg
   ```

---

## ERROR 10: "Network timeout" or "Connection refused"

### What This Means
Your computer can't reach Azure. It's either blocked or Azure isn't responding.

### Why It Happens
- Internet connection is slow or unstable
- Your firewall is blocking the connection
- Azure is temporarily down
- You typed the URL wrong

### How to Fix It

**Check your internet:**
1. Open a different website (like google.com)
2. Does it load?
3. If no, your internet is down - fix that first

**If internet is OK:**
1. Wait 1-2 minutes
2. Refresh the page
3. Try again

**If still stuck:**
1. Close your browser completely
2. Open a fresh browser window
3. Try the URL again

---

## ERROR 11: "502 Bad Gateway"

### What This Means
There's a problem between you and your app.

### Why It Happens
- Your app crashed
- Azure is restarting it
- There's a configuration error

### How to Fix It

1. Wait 2-3 minutes (Azure might be restarting)
2. Refresh the page
3. Try again

**If it keeps happening:**
1. Your app might have a problem
2. Check the logs:
   ```
   az containerapp logs show --name fpa-copilot-backend --resource-group fpa-copilot-rg
   ```
3. Look for red text that says "ERROR"

---

## ERROR 12: "Upload failed" or "File not found"

### What This Means
You tried to upload a file but something went wrong.

### Why It Happens
- The file format is wrong
- The file is too large
- Your app has an error

### How to Fix It

1. Make sure it's a CSV file (not Excel, Word, etc.)
2. Make sure it's less than 10MB
3. Try with a different file
4. If nothing works, check the logs:
   ```
   az containerapp logs show --name fpa-copilot-backend --resource-group fpa-copilot-rg
   ```

---

## ERROR 13: "Access Denied" or "Unauthorized"

### What This Means
You don't have permission to do something in Azure.

### Why It Happens
- Your Azure account doesn't have the right permissions
- You're logged into the wrong Azure account
- Your Azure subscription expired or isn't valid

### How to Fix It

1. Check which Azure account you're using:
   ```
   az account show
   ```

2. If it's the wrong account, log out and log back in:
   ```
   az logout
   ```
   Then: `az login` and log in with the correct account

3. Check your subscription is valid at https://portal.azure.com

---

## When You're Really Stuck

If none of these help:

1. **Read the error message carefully** - it usually tells you what's wrong
2. **Check the logs** - they contain more details:
   ```
   az containerapp logs show --name fpa-copilot-backend --resource-group fpa-copilot-rg
   ```
3. **Look at the full guides:**
   - `SETUP_FOR_NON_TECHNICAL_USERS.md`
   - `DEPLOYMENT_GUIDE.md`
4. **Try a fresh start:**
   - Close Terminal completely
   - Open a new Terminal window
   - Start from Step 4 of SIMPLE_CHECKLIST.md

---

## Getting Detailed Error Information

If something goes wrong during deployment, look at the logs:

```
az containerapp logs show --name fpa-copilot-backend --resource-group fpa-copilot-rg
```

This shows what your application is doing. Red text = errors.

---

## It's OK If Something Goes Wrong!

- The script is safe - you can run it again
- Your data is safe in Azure
- Nothing is permanent
- Errors are normal and fixable

**You've got this!** 💪
