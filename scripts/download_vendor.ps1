# Downloads Bootstrap 4.5.2, jQuery 3.5.1, and Popper 1.16.1 into static/vendor
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$dest = Join-Path $root '..\static\vendor' | Resolve-Path -Relative
$dest = (Resolve-Path (Join-Path $root '..\static\vendor')).ProviderPath
New-Item -ItemType Directory -Force -Path $dest\bootstrap\css | Out-Null
New-Item -ItemType Directory -Force -Path $dest\bootstrap\js | Out-Null
New-Item -ItemType Directory -Force -Path $dest\jquery | Out-Null
New-Item -ItemType Directory -Force -Path $dest\popper | Out-Null

$files = @(
  @{ url = 'https://code.jquery.com/jquery-3.5.1.min.js'; out = "$dest\jquery\jquery.min.js" },
  @{ url = 'https://cdn.jsdelivr.net/npm/popper.js@1.16.1/dist/umd/popper.min.js'; out = "$dest\popper\popper.min.js" },
  @{ url = 'https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css'; out = "$dest\bootstrap\css\bootstrap.min.css" },
  @{ url = 'https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js'; out = "$dest\bootstrap\js\bootstrap.min.js" }
)

foreach ($f in $files) {
  Write-Host "Downloading $($f.url) ..."
  try {
    Invoke-WebRequest -Uri $f.url -OutFile $f.out -UseBasicParsing -ErrorAction Stop
    Write-Host "Saved to $($f.out)"
  } catch {
    Write-Host "Failed to download $($f.url): $_" -ForegroundColor Red
  }
}

Write-Host "Done. Vendor assets are in static/vendor. Update references if necessary."
