# ✅ Simple Deployment Checklist

Follow this step-by-step. Check off each box as you complete it.

---

## BEFORE YOU START

- [ ] You have a Mac or computer
- [ ] You have internet connection
- [ ] You have 30 minutes of free time (for first deployment)
- [ ] You have an Azure account (create at https://azure.microsoft.com if needed)

---

## STEP 1: INSTALL TOOLS (15 minutes)

### Install Azure CLI

- [ ] Open Terminal (search "Terminal" in Spotlight)
- [ ] Copy this line exactly:
  ```
  brew install azure-cli
  ```
- [ ] Paste into Terminal and press Enter
- [ ] Wait for ✓ checkmark to appear
- [ ] Check it worked by typing: `az --version`
- [ ] You should see a version number

### Install Docker

- [ ] Go to https://www.docker.com/products/docker-desktop
- [ ] Click blue **"Download"** button
- [ ] Choose the right Mac version (Apple Silicon or Intel)
- [ ] Open the downloaded file
- [ ] Drag Docker icon to Applications folder
- [ ] Open Applications → Double-click Docker
- [ ] Wait for Docker icon in top menu bar (might take 2 minutes)
- [ ] Check it worked by typing in Terminal: `docker --version`
- [ ] You should see a version number

---

## STEP 2: GET YOUR API KEY (5 minutes)

- [ ] Go to https://console.anthropic.com/account/keys
- [ ] Log in if needed
- [ ] Click **"Create Key"** or **"Generate Key"**
- [ ] You'll see a string starting with `sk-ant-`
- [ ] Copy the entire string
- [ ] Save it in a text file (you'll need it next)
- [ ] ⚠️ Don't share this with anyone - it's secret!

---

## STEP 3: LOG INTO AZURE (5 minutes)

- [ ] Open Terminal
- [ ] Type or paste: `az login`
- [ ] Press Enter
- [ ] Your web browser opens
- [ ] Log in with your Azure email and password
- [ ] Close the browser when done
- [ ] Check Terminal - you should see "successfully authenticated"

---

## STEP 4: SET YOUR API KEY (2 minutes)

- [ ] Open Terminal
- [ ] Type this (replace `sk-ant-XXX...` with your actual key from Step 2):
  ```
  export ANTHROPIC_API_KEY="sk-ant-XXX..."
  ```
- [ ] Press Enter
- [ ] If no error message, you're good!

**Example:**
If your key is `sk-ant-abc123`, type:
```
export ANTHROPIC_API_KEY="sk-ant-abc123"
```

---

## STEP 5: GO TO THE PROJECT FOLDER (1 minute)

- [ ] Open Terminal (or use the same one)
- [ ] Type: `cd /Users/adedotunadebiaye/fpa-copilot`
- [ ] Press Enter
- [ ] Type: `pwd`
- [ ] Press Enter
- [ ] You should see: `/Users/adedotunadebiaye/fpa-copilot`

---

## STEP 6: RUN THE DEPLOYMENT (15 minutes)

- [ ] Type: `./deploy.sh`
- [ ] Press Enter
- [ ] **DO NOT CLOSE TERMINAL** - it will run for ~15 minutes
- [ ] Watch the text scroll by
- [ ] You'll see progress messages:
  - ✓ Prerequisites met
  - ✓ Resource group created
  - ✓ Container Registry created
  - ✓ Backend image built
  - ✓ Backend image pushed
  - ✓ Frontend image built
  - ✓ Frontend image pushed
  - ✓ Backend deployed
  - ✓ Frontend deployed

### When It's Done

- [ ] You see "Deployment Complete"
- [ ] You see two URLs:
  - Frontend: `https://fpa-copilot-frontend.azurecontainerapps.io`
  - Backend: `https://fpa-copilot-backend.azurecontainerapps.io`
- [ ] Copy these URLs and save them!

---

## STEP 7: TEST THE APP (5 minutes)

### Test 7A: Check Backend

- [ ] Open a web browser
- [ ] Paste your Backend URL with `/status` at the end:
  ```
  https://fpa-copilot-backend.azurecontainerapps.io/status
  ```
- [ ] Press Enter
- [ ] You should see text with `"status": "ok"`
- [ ] ✅ Backend is working!

### Test 7B: Open Frontend

- [ ] Open a new browser tab
- [ ] Paste your Frontend URL:
  ```
  https://fpa-copilot-frontend.azurecontainerapps.io
  ```
- [ ] Press Enter
- [ ] You should see a web page
- [ ] ✅ Frontend is working!

### Test 7C: Upload a File (Optional)

- [ ] On the frontend page, find the upload area
- [ ] Upload any CSV file or this one:
  `/Users/adedotunadebiaye/fpa-copilot/data/sample_budget_data.csv`
- [ ] Page should show "Ready" or similar
- [ ] ✅ Upload works!

### Test 7D: Ask a Question (Optional)

- [ ] Type: "What was the total revenue?"
- [ ] Click Send/Ask button
- [ ] Wait 2-3 seconds
- [ ] You should see an answer
- [ ] ✅ Everything works!

---

## ✅ DONE!

You've successfully deployed your app to Azure! 🎉

Your app is now live and accessible on the internet.

**Frontend:** `https://fpa-copilot-frontend.azurecontainerapps.io`

**Backend:** `https://fpa-copilot-backend.azurecontainerapps.io`

---

## SOMETHING WENT WRONG?

See **SETUP_FOR_NON_TECHNICAL_USERS.md** troubleshooting section:

- [ ] Check the error message Terminal shows
- [ ] Look for the matching problem in the guide
- [ ] Follow the solution
- [ ] Try again

**Common fixes:**
- "Azure CLI not found" → Run: `brew install azure-cli`
- "Docker not found" → Start Docker Desktop
- "API key not set" → Run Step 4 again
- "Not authenticated" → Run: `az login` and log in again

---

## NOTES FOR NEXT TIME

If you close Terminal, you'll need to do Step 4 again:
```
export ANTHROPIC_API_KEY="sk-ant-..."
```

But you only do this once per Terminal session.

---

## CONGRATULATIONS! 🚀

Your application is now deployed to Azure and live on the internet!

Anyone with your Frontend URL can now:
- Upload data files
- Ask financial questions
- Get answers with traces

**You did it!** 🎉
