# RenForge 2-tik Commit+Push (standalone v2)
# - Varsayilan: git add -u (izlenen dosyalar)
# - Eger sadece yeni (untracked) dosyalar varsa: popup ile "Ekle (git add -A)?" diye sorar.
# - Stage sonrasi hicbir sey yoksa commit denemez.

Set-Location -LiteralPath $PSScriptRoot

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName Microsoft.VisualBasic

function Msg([string]$text, [string]$title="RenForge Push") {
  [System.Windows.Forms.MessageBox]::Show($text, $title, 'OK', 'Information') | Out-Null
}

function Fail([string]$text) {
  [System.Windows.Forms.MessageBox]::Show($text, "RenForge Push - Hata", 'OK', 'Error') | Out-Null
  exit 1
}

function AskYesNo([string]$text, [string]$title="RenForge Push") {
  $res = [System.Windows.Forms.MessageBox]::Show($text, $title, 'YesNo', 'Question')
  return ($res -eq [System.Windows.Forms.DialogResult]::Yes)
}

# Git repo kontrolu
git rev-parse --is-inside-work-tree *> $null
if ($LASTEXITCODE -ne 0) {
  Fail "Bu klasor bir git repo degil. Dosyalari repo kokune kopyaladigindan emin ol:`n$PSScriptRoot"
}

# Durum oku
$status = git status --porcelain
$hasAny = -not [string]::IsNullOrWhiteSpace($status)

# Mesaj al (degisiklik yoksa bile isterse sadece push yapar)
$msg = [Microsoft.VisualBasic.Interaction]::InputBox(
  "Commit mesajini yaz (bos birakirsan WIP atar).`nDegisiklik yoksa sadece push dener.",
  "RenForge Commit Mesaji",
  ""
)
$wip = [string]::IsNullOrWhiteSpace($msg)
if ($wip) { $msg = "WIP: " + (Get-Date -Format 'yyyy-MM-dd HH:mm') }

try {
  if ($hasAny) {
    # 1) Once tracked degisiklikleri stage et
    git add -u

    # 2) Eger stage edilen yoksa ama untracked varsa, sorup ekle
    $staged = git diff --cached --name-only
    if ([string]::IsNullOrWhiteSpace($staged)) {
      # Untracked var mi?
      $untracked = git ls-files --others --exclude-standard
      if (-not [string]::IsNullOrWhiteSpace($untracked)) {
        $ok = AskYesNo ("Yeni dosyalar var (untracked).`nHepsini commit'e dahil edeyim mi?`n`nIpuclari:`n- Evet: git add -A (hepsini ekler)`n- Hayir: sadece push dener / cikis") "RenForge Push"
        if ($ok) {
          git add -A
          $staged = git diff --cached --name-only
        } else {
          Msg "Yeni dosyalar commit'e eklenmedi. Push deneniyor (degisiklik yoksa zaten bir sey olmayabilir)." "RenForge Push"
        }
      }
    }

    # 3) Hala staged yoksa commit deneme
    $staged2 = git diff --cached --name-only
    if (-not [string]::IsNullOrWhiteSpace($staged2)) {
      git commit -m "$msg"
      if ($LASTEXITCODE -ne 0) { Fail "Commit atilamadi. Konsolda hata var." }
    } else {
      # nothing staged -> commit skip
      # continue to push
    }
  }

  # Push (ilk kez upstream ayarla)
  $branch = (git rev-parse --abbrev-ref HEAD).Trim()
  $up = git rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>$null

  if (-not $up) {
    git push -u origin $branch
  } else {
    git push
  }

  if ($LASTEXITCODE -eq 0) {
    Msg "Tamam! Push basarili." "RenForge Push"
    exit 0
  } else {
    Fail "Push tamamlanamadi. Konsol cikisina bak."
  }
} catch {
  Fail ("Hata: " + $_.Exception.Message)
}
