# DIY HUE STUDIO — Flask Demo

Run locally:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

Download vendor assets (Bootstrap, jQuery, Popper):

Run the included PowerShell script to download local copies into `static/vendor`:

```powershell
cd scripts
.\download_vendor.ps1
```

After that the app will reference local copies of Bootstrap and JS.
