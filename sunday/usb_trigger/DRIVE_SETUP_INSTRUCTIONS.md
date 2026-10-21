# How to Setup the 1TB External Drive

To enable the automatic plug-and-play functionality, you need to label your 1TB external drive as `SUNDAY_DRIVE`. Here are the steps to do this on your Windows laptop:

1. **Connect the 1TB Drive:** Plug your external hard drive into your HP Pavilion.
2. **Open "This PC":** Open File Explorer and click on "This PC" on the left sidebar.
3. **Rename the Drive:**
   - Locate your 1TB external drive in the list of "Devices and drives".
   - Right-click on the drive and select **Rename**.
   - Type exactly `SUNDAY_DRIVE` (all caps, with the underscore) and press Enter.
   - If prompted for administrator permissions, click Continue.
4. **Copy the Codebase:**
   - Copy the entire `Sunday` repository folder to the root of the `SUNDAY_DRIVE`.
   - Copy the `bootstrap_sunday.bat` file to the root of the `SUNDAY_DRIVE`.
5. **Set up the Listener:**
   - Copy the `usb_listener.ps1` file to your laptop's Startup folder so it runs in the background automatically when you turn on your laptop. (Press `Win + R`, type `shell:startup`, and hit Enter to open the folder).
   - *Note:* You may need to create a small shortcut to run the PowerShell script silently on startup.

Now, whenever you plug in the `SUNDAY_DRIVE`, the laptop will detect the label and automatically launch Sunday!
