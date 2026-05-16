# INAV Flight View - Standard Installation Guide

This method installs the application directly onto your system using your existing Python installation. It is more lightweight than the Portable version and creates a convenient Desktop shortcut.

## **Prerequisites**
- **Python 3.10 or newer** must be installed on your computer.
- If you don't have Python, the installer will automatically direct you to the download page.

---

## **Installation Instructions**

1. **Download the Source Code**:
   Download and unzip the source code repository into a folder (e.g., `C:\Tools\INAV_Flight_View`).

2. **Run the Installer**:
   - Right-click the file named **`Install_INAV_Flight_View.ps1`**.
   - Select **"Run with PowerShell"**.

3. **Follow the Prompts**:
   - The script will check for Python.
   - It will create a "Virtual Environment" (a private space for the app's libraries).
   - It will download and install the required dependencies (PyQt6, PyVista, etc.).

4. **Launch the App**:
   Once finished, you will find a new shortcut named **"INAV Flight View"** on your Desktop. Double-click it to start!

---

## **Troubleshooting**

### **"Execution Policies" Error**
If Windows blocks the script from running, open a PowerShell window and run this command, then try again:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### **Updating the App**
If a new version is released, simply download the new code into the same folder and run the `Install_INAV_Flight_View.ps1` script again. It will update your libraries and shortcuts automatically.
