# 🚀 Non-Technical Setup Guide: Deploy to Azure in 5 Easy Steps

**Don't worry!** This guide explains everything in simple terms. No coding experience needed.

---

## What This Does (In Plain English)

You have an application (Phase 7) that works on your computer. We're going to send it to the cloud (Azure) so other people can use it on the internet.

Think of it like:
- **Your computer** = Your home kitchen
- **Azure cloud** = A restaurant that's open to the public
- **This guide** = Steps to move your kitchen to the restaurant

---

## Step 1: Get What You Need Installed (10 minutes)

### 1A: Install Azure CLI (The Cloud Tool)

This is software that lets you control Azure (the cloud service).

**For Mac:**

1. Open Terminal (search "Terminal" in Spotlight)
2. Copy and paste this entire line:
   ```
   brew install azure-cli
   ```
3. Press **Enter**
4. Wait for it to finish (you'll see a checkmark ✓)

**If you get "brew not found":**
- You need Homebrew first. Run this:
  ```
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```
- Then try the azure-cli command above

### 1B: Install Docker (The Container Tool)

This is software that packages your application into a box that can run anywhere.

**For Mac:**

1. Go to https://www.docker.com/products/docker-desktop
2. Click the big blue **"Download"** button
3. Choose the right version for your Mac:
   - If you have an **Apple Silicon/M1/M2/M3 Mac**: Download "Apple Silicon"
   - If you have an **Intel Mac**: Download "Intel Chip"
4. Open the downloaded file
5. Drag the Docker icon to the Applications folder
6. Open Applications folder and double-click Docker
7. Wait for it to start (you'll see the Docker icon in the top menu bar)

**To check it worked:**
- Open Terminal
- Copy and paste: `docker --version`
- You should see a version number (like "Docker version 24.0.0")

---

## Step 2: Get Your API Key (5 minutes)

This is like a password that lets your application talk to Claude (the AI).

1. Go to: https://console.anthropic.com/account/keys
2. You may need to log in (use your Anthropic/email account)
3. Look for a button that says **"Create Key"** or **"Generate Key"**
4. Click it
5. You'll see a long string that starts with `sk-ant-`
6. **Copy the entire string** (it's your secret key)
7. Paste it somewhere safe (like a text file) - you'll need it in the next step

**Important:** This key is like a password. Don't share it with anyone.

---

## Step 3: Log Into Azure (5 minutes)

This is where you tell Azure who you are.

**What you need first:**
- An Azure account (create one at https://azure.microsoft.com if you don't have one)
- A subscription (Azure gives you free credits)

**To log in:**

1. Open Terminal
2. Copy and paste this:
   ```
   az login
   ```
3. Press **Enter**
4. Your web browser will automatically open
5. Log in with your Azure account email and password
6. You'll see a message saying you're authenticated
7. Close the browser window

**Done!** You're now connected to Azure.

---

## Step 4: Copy Your API Key to Your Computer (3 minutes)

Now we need to tell your computer about that API key.

1. Open Terminal
2. Copy this line (but replace `sk-ant-XXX...` with your actual key from Step 2):
   ```
   export ANTHROPIC_API_KEY="sk-ant-XXX..."
   ```
3. Paste the entire line into Terminal
4. Press **Enter**

**Example:**
If your key is `sk-ant-abc123def456`, you would type:
```
export ANTHROPIC_API_KEY="sk-ant-abc123def456"
```

**Note:** This only sets it for this Terminal session. If you close Terminal and open a new one, you'll need to do this again. That's OK!

---

## Step 5: Run The Deployment (15 minutes)

This is the main part - sending your app to Azure.

1. Open Terminal
2. Go to your project folder by copying and pasting this:
   ```
   cd /Users/adedotunadebiaye/fpa-copilot
   ```
3. Press **Enter**
4. Now run the deployment script:
   ```
   ./deploy.sh
   ```
5. Press **Enter**

**What happens next:**

The script will start doing things. You'll see text appearing on the screen. Here's what to expect:

```
=== FP&A Copilot Azure Deployment ===

Step 1: Checking prerequisites...
✓ Prerequisites met

Step 2: Checking Azure subscription...
✓ Using subscription: abc123...

Step 3: Creating/verifying resource group...
✓ Resource group 'fpa-copilot-rg' exists
```

**Just wait.** Don't close Terminal. The script will:
- Create a folder in Azure to store your app
- Create a storage box for your Docker images
- Build your backend (the brain of the app)
- Build your frontend (the interface users see)
- Send these to Azure
- Start running them

**This takes about 15 minutes.** Go grab a coffee! ☕

### What You're Looking For

At the very end, you should see something like:

```
=== Deployment Complete ===

Access your application:
  Frontend: https://fpa-copilot-frontend.azurecontainerapps.io
  Backend:  https://fpa-copilot-backend.azurecontainerapps.io

✓ Deployment Successful
```

**Save those URLs!** You'll need them to test your app.

---

## Step 6: Test Your App (5 minutes)

Now let's make sure everything works.

### 6A: Test the Backend (Server)

1. Open a web browser (Chrome, Safari, etc.)
2. Copy this URL into the address bar (replace the example with yours):
   ```
   https://fpa-copilot-backend.azurecontainerapps.io/status
   ```
3. Press **Enter**

**What you should see:**
```json
{
  "status": "ok",
  "version": "0.7",
  "guardrails": {...}
}
```

If you see this: ✅ **Backend is working!**

If you see an error: Try waiting 1-2 minutes and refresh the page. Sometimes Azure needs time to start.

### 6B: Test the Frontend (The App Users See)

1. Copy this URL into your browser:
   ```
   https://fpa-copilot-frontend.azurecontainerapps.io
   ```
2. Press **Enter**

**What you should see:**
- A web page with your application
- A place to upload a CSV file
- A chat area to ask questions

If you see this: ✅ **Frontend is working!**

### 6C: Test Uploading a File

1. On the frontend page, look for an upload button or drag-and-drop area
2. Upload this file: `/Users/adedotunadebiaye/fpa-copilot/data/sample_budget_data.csv`
   - If you're not sure where to find it, just drag any CSV file you have
3. The page should show "Ready" or "Loaded"

If this works: ✅ **File upload is working!**

### 6D: Test Asking a Question

1. Type a question like: "What was the total revenue in Q1?"
2. Click the "Send" or "Ask" button
3. Wait 2-3 seconds
4. You should see an answer appear

If you see an answer: ✅ **Everything is working!**

---

## If Something Goes Wrong (Troubleshooting)

### Problem: "Azure CLI not found"

**Solution:**
1. You probably didn't install it in Step 1A
2. Try installing again:
   ```
   brew install azure-cli
   ```

### Problem: "Docker not found"

**Solution:**
1. You probably didn't install it or start it in Step 1B
2. Make sure Docker Desktop is running:
   - Look in Applications folder for "Docker"
   - Double-click to start it
   - Wait for the Docker icon to appear in the top menu bar

### Problem: "ANTHROPIC_API_KEY not set"

**Solution:**
1. You probably didn't do Step 4
2. Go back and run:
   ```
   export ANTHROPIC_API_KEY="your-key-here"
   ```
3. Then run the deployment again

### Problem: "Not authenticated with Azure"

**Solution:**
1. You probably didn't complete Step 3
2. Run this again:
   ```
   az login
   ```
3. Follow the browser login steps
4. Then try the deployment again

### Problem: "Deployment script won't start"

**Solution:**
1. Make sure you're in the right folder:
   ```
   cd /Users/adedotunadebiaye/fpa-copilot
   pwd
   ```
2. This should print: `/Users/adedotunadebiaye/fpa-copilot`
3. If it doesn't, change to the right folder
4. Then try:
   ```
   ./deploy.sh
   ```

### Problem: "Deployment script starts but then fails"

**Solution:**
1. The script will print an error message
2. Common reasons:
   - Azure credentials expired (run `az login` again)
   - Docker not running (start Docker Desktop)
   - API key wrong (check it in Step 2 again)
3. You can always run the script again - it's safe

### Problem: "The app URLs don't work"

**Solution:**
1. Sometimes Azure takes 2-3 minutes to start
2. Wait a few minutes
3. Try refreshing the page
4. If it still doesn't work, check the logs:
   ```
   az containerapp logs show --name fpa-copilot-backend --resource-group fpa-copilot-rg
   ```

---

## What You've Done

Congratulations! 🎉 You've:

1. ✅ Installed the tools needed
2. ✅ Got your API key
3. ✅ Logged into Azure
4. ✅ Deployed your app to the cloud
5. ✅ Tested that it works
6. ✅ Made it available on the internet

Your app is now live! People can visit your frontend URL and use it.

---

## Next Steps (Optional - For Later)

### If you want to make updates:

1. Make changes to your code
2. Open Terminal
3. Set your API key again:
   ```
   export ANTHROPIC_API_KEY="your-key-here"
   ```
4. Go to your project:
   ```
   cd /Users/adedotunadebiaye/fpa-copilot
   ```
5. Run the deployment again:
   ```
   ./deploy.sh
   ```

### If you want to delete everything:

If you want to stop paying for Azure and remove everything:

```
az group delete --name fpa-copilot-rg --yes
```

This deletes all your Azure resources. **Warning:** This removes your app from the internet!

---

## Getting Help

If you get stuck, here's what to do:

1. **Read the error message** - it usually tells you what's wrong
2. **Check the Troubleshooting section above**
3. **Look at the logs** - they contain more details:
   ```
   az containerapp logs show --name fpa-copilot-backend --resource-group fpa-copilot-rg
   ```

---

## Key Files (You probably don't need to look at these, but they're there)

- `deploy.sh` - The script that does everything
- `backend/Dockerfile` - Instructions for building the server
- `frontend/Dockerfile` - Instructions for building the app
- `requirements.txt` - List of software your app needs
- `DEPLOYMENT_GUIDE.md` - Technical version of this guide

---

## You Did It! 🚀

Your app is now deployed to Azure and accessible on the internet.

**Frontend URL:** `https://fpa-copilot-frontend.azurecontainerapps.io`
**Backend URL:** `https://fpa-copilot-backend.azurecontainerapps.io`

Share these URLs with people who want to use your app!

---

**Questions?** All the tools and instructions are above. You've got this! 💪
